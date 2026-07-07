"""Main orchestration engine — wires registry, bus, router, memory together."""

from __future__ import annotations

import asyncio
import contextlib
import os
import uuid
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from typing import Any

from .approval import ApprovalManager
from .bus import MessageBus
from .chat import ChatManager
from .costs import CostLedger
from .dependency_scanner import DependencyScanner
from .llm import LLMManager
from .logger import TaskLogger
from .ltm import LongTermMemory
from .memory import AgencyMemory
from .metrics import MetricsCollector
from .models import (
    AgencyConfig,
    AgencyTask,
    ApprovalRequest,
    BusMessage,
    ChatMessage,
    ChatThread,
    CostRecord,
    HealthCheck,
    HealthStatus,
    IntelReport,
    LLMMessage,
    LLMResponse,
    MessageRole,
    MetricPoint,
    ModuleStatus,
    Notification,
    NotificationChannel,
    Project,
    RepoCategory,
    RepoNode,
    RiskLevel,
    TaskStatus,
    Tenant,
    WhiteLabelConfig,
)
from .notifications import NotificationManager
from .registry import RepoRegistry
from .router import TaskRouter
from .runner import CloneManager, RepoRunner
from .scheduler import WorkflowScheduler
from .security import AuditLogger, InputSanitizer, NetworkPolicy, SecretsManager
from .workflows import WorkflowEngine


class AgencyEngine:
    """Central engine for the One Person Agency."""

    def __init__(self, config: AgencyConfig | None = None) -> None:
        self.config = config or AgencyConfig()
        self.secrets = SecretsManager()
        github_token_secret = self.secrets.register(
            "github_token",
            env_var="GITHUB_TOKEN",
            config_value=self.config.github_token,
        )
        self.registry = RepoRegistry(
            data_dir=self.config.data_dir,
            github_token=github_token_secret.value,
        )
        self.bus = MessageBus()
        self.router = TaskRouter(self.registry, self.bus, config=self.config)
        self.memory = AgencyMemory(
            data_dir=self.config.data_dir,
            backend=self.config.memory_backend,
        )
        self.audit = AuditLogger(self.memory)
        self.network_policy = NetworkPolicy(
            allowlist=self.config.security.network_allowlist,
            blocklist=self.config.security.network_blocklist,
        )
        self.runner = RepoRunner(
            CloneManager(os.path.join(self.config.data_dir, "repos")),
            network_policy=self.network_policy,
            audit_logger=self.audit,
        )
        self.dependency_scanner = DependencyScanner(data_dir=self.config.data_dir)
        self.approval_manager = ApprovalManager()
        self.chat = ChatManager()
        self.metrics = MetricsCollector(retention_hours=self.config.metrics_retention_hours)
        self.notifications = NotificationManager(config=self.config.notifications)
        self.workflows = WorkflowEngine(config=self.config)
        self.cost_ledger = CostLedger(self.memory)
        self.llm_manager = LLMManager(self.config.llm, self.memory, ledger=self.cost_ledger)
        self.scheduler = WorkflowScheduler(self)
        self.task_logger = TaskLogger(self.config.data_dir)
        self.scheduler.load_schedules()
        self.long_term_memory = LongTermMemory(self.memory)
        self._running = False
        self._worker_task: asyncio.Task[Any] | None = None
        self._task_queue: asyncio.Queue[AgencyTask] = asyncio.Queue()
        self._tasks: dict[str, AgencyTask] = {}
        self._load_tasks()
        self._wire_events()

    def _wire_events(self) -> None:
        """Wire bus events to notifications and metrics."""
        self.bus.subscribe("*", self._on_bus_message)

    def _on_bus_message(self, message: BusMessage) -> None:
        """Handle bus messages for observability and notifications."""
        topic = message.topic
        payload = message.payload

        # Metrics
        if topic.startswith("task."):
            status = topic.split(".", 1)[1]
            self.metrics.increment("tasks_total", labels={"status": status})
        elif topic == "registry.sync":
            self.metrics.increment("registry_sync_total")
            self.metrics.gauge("registry_modules", payload.get("count", 0))
        elif topic == "intel.scout":
            self.metrics.increment("intel_scout_total", labels={"type": payload.get("type", "unknown")})
        elif topic.startswith("workflow."):
            self.metrics.increment("workflow_events_total", labels={"topic": topic})

        # Notifications (async fire-and-forget)
        asyncio.create_task(self.notifications.on_bus_message(message))

    async def notify(
        self,
        channel: NotificationChannel,
        title: str,
        body: str,
        recipient: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Notification:
        """Send a notification through the configured manager."""
        return await self.notifications.send(channel, title, body, recipient, payload)

    async def broadcast_notification(
        self,
        title: str,
        body: str,
        channels: list[NotificationChannel] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> list[Notification]:
        """Broadcast a notification to multiple channels."""
        return await self.notifications.broadcast(title, body, channels, payload)

    def record_metric(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> MetricPoint:
        """Record a custom metric."""
        return self.metrics.record(name, value, labels)

    def register_health_check(self, name: str, check: Any) -> None:
        """Register a health check with the metrics collector."""
        self.metrics.register_health_check(name, check)

    def _default_health_checks(self) -> None:
        """Register built-in health checks."""
        def worker_check() -> HealthCheck:
            status = HealthStatus.HEALTHY if self._running else HealthStatus.UNHEALTHY
            return HealthCheck(name="worker", status=status, message="Task worker is running" if self._running else "Task worker is stopped")

        def registry_check() -> HealthCheck:
            count = len(self.registry.modules)
            status = HealthStatus.HEALTHY if count > 0 else HealthStatus.DEGRADED
            return HealthCheck(name="registry", status=status, message=f"{count} modules registered")

        self.register_health_check("worker", worker_check)
        self.register_health_check("registry", registry_check)

    async def start_worker(self) -> None:
        if self._running:
            return
        self._running = True
        self._default_health_checks()
        self._worker_task = asyncio.create_task(self._worker_loop())
        await self.scheduler.start()

    async def stop_worker(self) -> None:
        if not self._running:
            return
        self._running = False
        await self.scheduler.stop()
        if self._worker_task is not None:
            self._worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._worker_task
            self._worker_task = None

    async def _worker_loop(self) -> None:
        while self._running:
            try:
                task = await asyncio.wait_for(self._task_queue.get(), timeout=0.5)
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            await self._execute_task(task)

    def get_task(self, task_id: str) -> AgencyTask | None:
        return self._tasks.get(task_id)

    async def approve_task(self, task_id: str, by: str = "operator") -> ApprovalRequest | None:
        """Approve a pending risky task by task id."""
        req = self.approval_manager.approve_by_task(task_id, by)
        if req is not None:
            self.audit.log("task.approved", by, task_id, {"approval_id": req.id})
            await self.task_logger.info(
                task_id,
                "Approval granted",
                actor="approval",
                **{"approval_id": req.id, "approved_by": by},
            )
        return req

    async def reject_task(self, task_id: str, by: str = "operator") -> ApprovalRequest | None:
        """Reject a pending risky task by task id."""
        request_id = self.approval_manager._by_task.get(task_id)
        if request_id is None:
            return None
        req = self.approval_manager.reject(request_id, by)
        if req is not None:
            self.audit.log("task.rejected", by, task_id, {"approval_id": req.id})
            await self.task_logger.info(
                task_id,
                "Approval rejected",
                actor="approval",
                **{"approval_id": req.id, "rejected_by": by},
            )
        return req

    def list_pending_approvals(self) -> list[ApprovalRequest]:
        """Return all approval requests awaiting human review."""
        return self.approval_manager.list_pending()

    def get_chat_thread(self, thread_id: str) -> ChatThread | None:
        """Return a chat thread by id."""
        return self.chat.get_thread(thread_id)

    async def chat_message(
        self,
        thread_id: str | None,
        content: str,
        title: str | None = None,
    ) -> tuple[ChatThread, ChatMessage, AgencyTask]:
        """Store a user message, dispatch it as a task, and return an agency reply.

        The user's message is routed as a task intent. An agency acknowledgment
        message is added to the thread immediately, linking back to the task so
        clients can poll for completion.
        """
        if thread_id is None:
            thread = self.chat.create_thread(title=title or "New conversation")
        else:
            existing = self.chat.get_thread(thread_id)
            thread = existing or self.chat.create_thread(title=title or f"Thread {thread_id}")
            if existing is None:
                thread.id = thread_id
                self.chat._threads[thread_id] = thread

        self.chat.add_message(thread.id, MessageRole.USER, content)

        task = await self.dispatch(content, {"source": "chat", "thread_id": thread.id})

        await self.task_logger.info(
            task.id,
            "Chat message dispatched as task",
            actor="chat",
            **{"thread_id": thread.id},
        )

        module_name = task.module_id or task.category.value if task.category else "agency"
        reply_text = (
            f"Dispatched task `{task.id}` to **{module_name}**. "
            "I'll update here once it completes."
        )
        agency_message = self.chat.add_message(
            thread.id,
            MessageRole.AGENCY,
            reply_text,
            task_id=task.id,
        )
        return thread, agency_message, task

    def list_memory_keys(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return a list of stored memory keys with their values and updated_at times.

        This is a lightweight wrapper over the memory backend; full pagination and
        value size limits can be added once memory grows.
        """
        # AgencyMemory currently stores opaque values; expose recent events plus
        # any explicit keys. For sqlite we introspect the memory table directly.
        if self.memory.backend == "sqlite":
            import sqlite3

            with sqlite3.connect(self.memory.db_path) as conn:
                rows = conn.execute(
                    "SELECT key, value, updated_at FROM memory ORDER BY updated_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
                return [
                    {"key": r[0], "value": self._safe_load_json(r[1]), "updated_at": r[2]}
                    for r in rows
                ]
        # JSON backend
        return [
            {"key": k, "value": v, "updated_at": None}
            for k, v in list(self.memory._data.items())[:limit]
        ]

    @staticmethod
    def _safe_load_json(value: str) -> Any:
        import json

        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    def set_memory(self, key: str, value: Any) -> None:
        """Set a value in agency memory."""
        self.memory.set(key, value)

    # ---------- Multi-tenancy scaffolding ----------

    def create_tenant(self, name: str) -> Tenant:
        """Create a new tenant and persist it."""
        tenant = Tenant(id=f"tenant_{uuid.uuid4().hex[:8]}", name=name)
        self.memory.set(f"tenant:{tenant.id}", tenant.model_dump(mode="json"))
        tenants = self.memory.get("tenants:index", [])
        tenants.append(tenant.id)
        self.memory.set("tenants:index", tenants)
        self.audit.log("tenant.created", "operator", tenant.id, {"name": name})
        return tenant

    def list_tenants(self) -> list[Tenant]:
        """Return all persisted tenants."""
        tenants = []
        for tenant_id in self.memory.get("tenants:index", []):
            data = self.memory.get(f"tenant:{tenant_id}")
            if data:
                try:
                    tenants.append(Tenant.model_validate(data))
                except Exception:
                    continue
        return tenants

    def create_project(self, tenant_id: str, name: str, config: dict[str, Any] | None = None) -> Project:
        """Create a new project under a tenant."""
        project = Project(
            id=f"project_{uuid.uuid4().hex[:8]}",
            tenant_id=tenant_id,
            name=name,
            config=config or {},
        )
        self.memory.set(f"project:{project.id}", project.model_dump(mode="json"))
        projects = self.memory.get("projects:index", [])
        projects.append(project.id)
        self.memory.set("projects:index", projects)
        self.audit.log("project.created", "operator", project.id, {"tenant_id": tenant_id, "name": name})
        return project

    def list_projects(self, tenant_id: str | None = None) -> list[Project]:
        """Return projects, optionally filtered by tenant."""
        projects = []
        for project_id in self.memory.get("projects:index", []):
            data = self.memory.get(f"project:{project_id}")
            if data:
                try:
                    project = Project.model_validate(data)
                    if tenant_id is None or project.tenant_id == tenant_id:
                        projects.append(project)
                except Exception:
                    continue
        return projects

    def set_project_secret(self, project_id: str, key: str, value: str) -> None:
        """Store an encrypted-at-rest secret for a project (plaintext in scaffolding)."""
        secrets = self.memory.get(f"project:{project_id}:secrets", {})
        secrets[key] = value
        self.memory.set(f"project:{project_id}:secrets", secrets)
        self.audit.log("project.secret.set", "operator", project_id, {"key": key})

    def get_project_secret(self, project_id: str, key: str) -> str | None:
        """Retrieve a project secret."""
        secrets = self.memory.get(f"project:{project_id}:secrets", {})
        return secrets.get(key)

    def get_white_label_config(self, project_id: str | None = None) -> dict[str, Any]:
        """Return white-label branding config for a project, or the default brand."""
        if project_id:
            stored = self.memory.get(f"project:{project_id}:white_label")
            if stored and isinstance(stored, dict):
                try:
                    config = WhiteLabelConfig.model_validate(stored)
                    return config.model_dump(mode="json", by_alias=True)
                except Exception:
                    pass
        return WhiteLabelConfig().model_dump(mode="json", by_alias=True)

    def list_tasks(self, limit: int = 50) -> list[AgencyTask]:
        sorted_tasks = sorted(self._tasks.values(), key=lambda t: t.created_at, reverse=True)
        return sorted_tasks[:limit]

    def _append_chat_result(self, task: AgencyTask) -> None:
        """Append a completion message to the chat thread linked to a task, if any."""
        thread_id = task.payload.get("thread_id")
        if not thread_id:
            return
        if task.status == TaskStatus.COMPLETED:
            summary = task.result or {}
            content = f"Task `{task.id}` completed"
            if isinstance(summary, dict):
                module = summary.get("module")
                if module:
                    content += f" via **{module}**"
                execution = summary.get("execution")
                if isinstance(execution, dict):
                    status = execution.get("status")
                    if status:
                        content += f" ({status})"
                    stdout = execution.get("stdout")
                    if stdout:
                        content += f"\n```\n{stdout[:500]}\n```"
            content += "."
        elif task.status == TaskStatus.FAILED:
            content = f"Task `{task.id}` failed: {task.error or 'Unknown error'}"
        elif task.status == TaskStatus.CANCELLED:
            content = f"Task `{task.id}` was cancelled."
        else:
            return
        self.chat.add_message(
            thread_id,
            MessageRole.AGENCY,
            content,
            task_id=task.id,
        )

    async def sync_repos(self, username: str | None = None) -> list[RepoNode]:
        """Sync all GitHub repos into the registry."""
        user = username or self.config.github_username
        discovered = await self.registry.discover(user)
        self.memory.log_event("registry.sync", {"username": user, "count": len(discovered)})
        return discovered

    def _load_tasks(self) -> None:
        """Restore persisted tasks into memory."""
        for data in self.memory.load_tasks():
            try:
                task = AgencyTask.model_validate(data)
                self._tasks[task.id] = task
            except Exception:
                continue

    def _persist_task(self, task: AgencyTask) -> None:
        """Save task state to memory."""
        self.memory.save_task(task.id, task.model_dump(mode="json"))

    async def dispatch(
        self,
        intent: str,
        payload: dict[str, Any] | None = None,
        tenant_id: str | None = None,
        project_id: str | None = None,
    ) -> AgencyTask:
        """Dispatch a task through the agency."""
        if self.config.security.sanitize_input:
            intent = InputSanitizer.sanitize_intent(intent)
            payload = InputSanitizer.sanitize_payload(payload or {})
        task = await self.router.route(intent, payload)
        task.tenant_id = tenant_id
        task.project_id = project_id
        self._tasks[task.id] = task
        self.memory.log_event("task.created", {"task_id": task.id, "intent": intent})
        await self.task_logger.info(
            task.id,
            "Task dispatched",
            actor="engine",
            **{
                "intent": intent,
                "module_id": task.module_id,
                "category": task.category.value if task.category else None,
            },
        )
        self._persist_task(task)
        self.audit.log(
            "task.dispatched",
            "operator",
            task.id,
            {"intent": intent, "module_id": task.module_id, "category": task.category.value if task.category else None},
        )
        await self._task_queue.put(task)
        return task

    async def llm_chat(
        self,
        messages: Sequence[LLMMessage],
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        task: AgencyTask | None = None,
    ) -> LLMResponse:
        """Send a chat request through the configured LLM provider."""
        return await self.llm_manager.chat(
            messages=messages,
            provider=provider,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            task=task,
        )

    def _resolve_module(self, module_id: str) -> RepoNode | None:
        """Resolve a module by id, falling back to ecosystem config stubs."""
        mod = self.registry.get(module_id)
        if mod is not None:
            return mod

        eco = self.config.ecosystem.get(module_id)
        if eco:
            repo_name = eco.get("repo", module_id)
            owner = eco.get("owner", self.config.github_username or "sahiixx")
            return RepoNode(
                id=module_id,
                name=repo_name,
                owner=owner,
                full_name=f"{owner}/{repo_name}",
                url=eco.get("url", f"https://github.com/{owner}/{repo_name}"),
                description=eco.get("role"),
                adapter_config=eco.get("adapter_config", {}),
            )
        return None

    def _risk_level_for_task(self, task: AgencyTask) -> RiskLevel:
        """Determine task risk from payload or target module."""
        payload_risk = task.payload.get("risk_level")
        if payload_risk:
            try:
                return RiskLevel(payload_risk.lower())
            except ValueError:
                pass
        if task.module_id:
            mod = self._resolve_module(task.module_id)
            if mod is not None:
                return mod.risk_level
        return RiskLevel.LOW

    def _requires_approval(self, risk_level: RiskLevel) -> bool:
        """High and critical risk tasks require human approval."""
        return risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}

    async def _execute_task(self, task: AgencyTask) -> None:
        """Execute a task by cloning and running the target module."""
        risk_level = self._risk_level_for_task(task)
        if self._requires_approval(risk_level) and not self.approval_manager.is_approved(task.id):
            req = self.approval_manager.request_approval(
                task,
                risk_level,
                f"Risky execution: {task.intent}",
            )
            task.status = TaskStatus.PENDING
            self.memory.log_event("task.awaiting_approval", {"task_id": task.id, "risk_level": risk_level.value})
            await self.task_logger.info(
                task.id,
                "Approval requested",
                actor="approval",
                **{"approval_id": req.id, "risk_level": risk_level.value, "reason": req.reason},
            )
            return

        task.status = TaskStatus.RUNNING
        task.started_at = task.started_at or datetime.now(timezone.utc)
        self.memory.log_event("task.running", {"task_id": task.id})
        await self.task_logger.info(
            task.id,
            "Task execution started",
            actor="engine",
            **{
                "module_id": task.module_id,
                "category": task.category.value if task.category else None,
            },
        )

        try:
            with self.metrics.timer("task_execution_latency_seconds", labels={"module": task.module_id or "none"}):
                if task.module_id:
                    mod = self._resolve_module(task.module_id)
                    if mod:
                        if not await self._run_dependency_scan_gate(mod, task):
                            return

                        if task.module_id.lower() == "t3mp3st":
                            # Use the safety-hardened T3MP3ST MCP adapter
                            from sahiixx_agency.adapters.security.t3mp3st_mcp import T3mp3stMcpAdapter

                            t3mp3st_adapter = T3mp3stMcpAdapter(
                                clone_base_dir=os.path.join(self.config.data_dir, "repos"),
                                approval_token=self.config.t3mp3st_approval_token,
                                network_policy=self.network_policy,
                                audit_logger=self.audit,
                            )
                            run_result = await t3mp3st_adapter.run(mod, task.payload)
                            task.result = {
                                "module": mod.name,
                                "category": mod.category.value,
                                "url": mod.url,
                                "capabilities": mod.capabilities,
                                "execution": run_result,
                            }
                        elif task.module_id.lower() in {"career-ops", "career_ops"}:
                            from sahiixx_agency.adapters.career.career_ops_adapter import CareerOpsAdapter

                            career_adapter = CareerOpsAdapter(
                                clone_base_dir=os.path.join(self.config.data_dir, "repos"),
                                network_policy=self.network_policy,
                                audit_logger=self.audit,
                            )
                            run_result = await career_adapter.run(mod, task.payload)
                            task.result = {
                                "module": mod.name,
                                "category": mod.category.value,
                                "url": mod.url,
                                "capabilities": mod.capabilities,
                                "execution": run_result,
                            }
                        elif task.module_id.lower() in {"hiring-agent", "hiring_agent"}:
                            from sahiixx_agency.adapters.hiring.hiring_agent_adapter import HiringAgentAdapter

                            hiring_adapter = HiringAgentAdapter(
                                clone_base_dir=os.path.join(self.config.data_dir, "repos"),
                                network_policy=self.network_policy,
                                audit_logger=self.audit,
                            )
                            run_result = await hiring_adapter.run(mod, task.payload)
                            task.result = {
                                "module": mod.name,
                                "category": mod.category.value,
                                "url": mod.url,
                                "capabilities": mod.capabilities,
                                "execution": run_result,
                            }
                        elif task.module_id.lower() in {"html-anything", "html_anything"}:
                            from sahiixx_agency.adapters.design.html_anything_adapter import HtmlAnythingAdapter

                            html_payload = dict(task.payload)
                            html_payload.setdefault("brief", task.intent)
                            html_adapter = HtmlAnythingAdapter(
                                clone_base_dir=os.path.join(self.config.data_dir, "repos"),
                                network_policy=self.network_policy,
                                audit_logger=self.audit,
                            )
                            run_result = await html_adapter.run(mod, html_payload)
                            task.result = {
                                "module": mod.name,
                                "category": mod.category.value,
                                "url": mod.url,
                                "capabilities": mod.capabilities,
                                "execution": run_result,
                            }
                        elif task.module_id.lower() == "openmontage":
                            from sahiixx_agency.adapters.video.open_montage_adapter import OpenMontageAdapter

                            om_adapter = OpenMontageAdapter(
                                clone_base_dir=os.path.join(self.config.data_dir, "repos"),
                                network_policy=self.network_policy,
                                audit_logger=self.audit,
                            )
                            run_result = await om_adapter.run(mod, task.payload)
                            task.result = {
                                "module": mod.name,
                                "category": mod.category.value,
                                "url": mod.url,
                                "capabilities": mod.capabilities,
                                "execution": run_result,
                            }
                        elif task.module_id:
                            # Generic fallback: infer entrypoint and run
                            from sahiixx_agency.adapters.generic_adapter import GenericAdapter

                            generic_adapter = GenericAdapter(
                                data_dir=self.config.data_dir,
                                timeout=task.payload.get("timeout", 120),
                                network_policy=self.network_policy,
                                audit_logger=self.audit,
                            )
                            run_result = await generic_adapter.run(mod, task.payload)
                            task.result = {
                                "module": mod.name,
                                "category": mod.category.value,
                                "url": mod.url,
                                "capabilities": mod.capabilities,
                                "execution": run_result,
                            }
                        self.metrics.increment("adapter_runs_total", labels={"adapter": task.module_id.lower()})
                        self.registry.set_status(mod.id, ModuleStatus.ACTIVE)
                        # Future: derive adapter pricing here for non-zero execution costs.
                        execution_amount = 0.0
                        if execution_amount:
                            self.cost_ledger.record(
                                CostRecord(
                                    tenant_id=task.tenant_id,
                                    project_id=task.project_id,
                                    task_id=task.id,
                                    category="execution",
                                    amount=execution_amount,
                                    currency="USD",
                                    description=f"Adapter run for {task.module_id}",
                                )
                            )
                    else:
                        task.result = {"note": "Module not found in registry."}
                else:
                    # No specific module — try to run a category adapter
                    category = task.category
                    if category:
                        task.result = await self._run_category_adapter(category, task)
                    else:
                        task.result = {
                            "note": "No module or category matched.",
                            "intent": task.intent,
                        }

                # Respect terminal statuses set by the dependency scan gate or adapters.
                # This prevents the category-adapter path (and any future adapter path)
                # from overwriting a terminal state with COMPLETED.
                if task.status in {TaskStatus.FAILED, TaskStatus.CANCELLED}:
                    return

            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now(timezone.utc)
            self.memory.log_event("task.completed", {"task_id": task.id})
            self.audit.log("task.completed", "worker", task.id, {"module_id": task.module_id})
            await self.task_logger.info(
                task.id,
                "Task completed",
                actor="engine",
                **{"module_id": task.module_id},
            )
        except Exception as exc:
            task.status = TaskStatus.FAILED
            task.error = str(exc)
            self.memory.log_event("task.failed", {"task_id": task.id, "error": str(exc)})
            self.metrics.increment("tasks_total", labels={"status": "failed"})
            self.audit.log("task.failed", "worker", task.id, {"error": str(exc)})
            await self.task_logger.error(
                task.id,
                "Task failed",
                actor="engine",
                **{"error": str(exc), "module_id": task.module_id},
            )
        finally:
            self._persist_task(task)
            self._append_chat_result(task)

    async def _run_dependency_scan_gate(self, mod: RepoNode, task: AgencyTask) -> bool:
        """Run the dependency scan when enabled and block execution on failure.

        Returns ``True`` when execution may proceed (scan passed or disabled).
        On failure, mutates ``task`` to FAILED, logs the audit event, and
        increments the failure metric.
        """
        if not self.config.security.dependency_scan_enabled:
            return True
        scan_report = await self.dependency_scanner.scan(mod)
        if scan_report.passed:
            return True
        task.status = TaskStatus.FAILED
        task.error = "Dependency vulnerability scan failed"
        task.result = {"dependency_scan": scan_report.model_dump(mode="json")}
        task.completed_at = datetime.now(timezone.utc)
        self.memory.log_event(
            "task.failed",
            {"task_id": task.id, "error": task.error},
        )
        await self.task_logger.error(
            task.id,
            "Dependency vulnerability scan failed",
            actor="engine",
            **{"failures": scan_report.failures, "command": scan_report.command},
        )
        self.metrics.increment("tasks_total", labels={"status": "failed"})
        self.audit.log(
            "dependency_scan.failed",
            "worker",
            task.id,
            scan_report.model_dump(mode="json"),
        )
        return False

    async def _run_category_adapter(self, category: RepoCategory, task: AgencyTask) -> dict[str, Any]:
        """Run the best module from a category."""
        modules = self.registry.by_category(category)
        if not modules:
            return {"note": f"No modules in category {category.value}"}
        # Pick the one with the most stars
        best = max(modules, key=lambda m: m.stars)
        if not await self._run_dependency_scan_gate(best, task):
            return {"dependency_scan": task.result.get("dependency_scan") if task.result else None}
        payload = task.payload
        run_result = await self.runner.run(
            best,
            command=payload.get("command", "run"),
            env=payload.get("env"),
            timeout=payload.get("timeout", 60),
        )
        return {
            "category": category.value,
            "module": best.name,
            "execution": run_result,
        }

    def stats(self) -> dict[str, Any]:
        """Return combined agency stats."""
        return {
            "config": self.config.model_dump(mode="json"),
            "registry": self.registry.stats(),
            "memory_events": len(self.memory.recent_events(limit=999999)),
            "metrics": self.metrics.summary(),
            "health": self.metrics.overall_health().value,
            "workflows": {
                "definitions": len(self.workflows.list_definitions()),
                "instances": len(self.workflows.list_instances()),
            },
            "notifications": len(self.notifications.history(limit=999999)),
        }

    async def run_intel_scout(
        self,
        report_type: str = "trending",
        languages: list[str] | None = None,
        min_stars: int = 50,
    ) -> IntelReport:
        """Run the GitHub intelligence scout."""
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "sahiixx-agency"}
        if self.config.github_token:
            headers["Authorization"] = f"Bearer {self.config.github_token}"

        repos: list[RepoNode] = []
        queries: list[str] = []
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")

        async with __import__("httpx").AsyncClient(timeout=30) as client:
            if report_type in ("trending", "velocity"):
                q = f"created:>{week_ago} stars:>{min_stars}"
                if languages:
                    q += " language:" + " language:".join(languages)
                queries.append(q)
                url = f"https://api.github.com/search/repositories?q={q}&sort=stars&order=desc&per_page=20"
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("items", []):
                        repos.append(self.registry._raw_to_node(item))

            if report_type in ("hidden_gems",):
                q = f"stars:100..1000 pushed:>{week_ago}"
                queries.append(q)
                url = f"https://api.github.com/search/repositories?q={q}&sort=stars&order=desc&per_page=15"
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("items", []):
                        repos.append(self.registry._raw_to_node(item))

        report = IntelReport(
            id=f"intel_{uuid.uuid4().hex[:8]}",
            report_type=report_type,  # type: ignore[arg-type]
            repos=repos,
            summary=f"Scout found {len(repos)} repos for type '{report_type}'.",
            raw_queries=queries,
        )
        self.memory.log_event("intel.scout", {"report_id": report.id, "type": report_type, "count": len(repos)})
        return report
