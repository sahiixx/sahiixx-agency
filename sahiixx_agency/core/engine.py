"""Main orchestration engine — wires registry, bus, router, memory together."""

from __future__ import annotations

import asyncio
import contextlib
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from .bus import MessageBus
from .memory import AgencyMemory
from .models import AgencyConfig, AgencyTask, IntelReport, ModuleStatus, RepoCategory, RepoNode, TaskStatus
from .registry import RepoRegistry
from .router import TaskRouter
from .runner import CloneManager, RepoRunner


class AgencyEngine:
    """Central engine for the One Person Agency."""

    def __init__(self, config: AgencyConfig | None = None) -> None:
        self.config = config or AgencyConfig()
        self.registry = RepoRegistry(
            data_dir=self.config.data_dir,
            github_token=self.config.github_token,
        )
        self.bus = MessageBus()
        self.router = TaskRouter(self.registry, self.bus, config=self.config)
        self.memory = AgencyMemory(
            data_dir=self.config.data_dir,
            backend=self.config.memory_backend,
        )
        self.runner = RepoRunner(CloneManager(os.path.join(self.config.data_dir, "repos")))
        self._running = False
        self._worker_task: asyncio.Task[Any] | None = None
        self._task_queue: asyncio.Queue[AgencyTask] = asyncio.Queue()
        self._tasks: dict[str, AgencyTask] = {}

    async def start_worker(self) -> None:
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())

    async def stop_worker(self) -> None:
        if not self._running:
            return
        self._running = False
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

    def list_tasks(self, limit: int = 50) -> list[AgencyTask]:
        sorted_tasks = sorted(self._tasks.values(), key=lambda t: t.created_at, reverse=True)
        return sorted_tasks[:limit]

    async def sync_repos(self, username: str | None = None) -> list[RepoNode]:
        """Sync all GitHub repos into the registry."""
        user = username or self.config.github_username
        discovered = await self.registry.discover(user)
        self.memory.log_event("registry.sync", {"username": user, "count": len(discovered)})
        return discovered

    async def dispatch(self, intent: str, payload: dict[str, Any] | None = None) -> AgencyTask:
        """Dispatch a task through the agency."""
        task = await self.router.route(intent, payload)
        self._tasks[task.id] = task
        self.memory.log_event("task.created", {"task_id": task.id, "intent": intent})
        await self._task_queue.put(task)
        return task

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

    async def _execute_task(self, task: AgencyTask) -> None:
        """Execute a task by cloning and running the target module."""
        task.status = TaskStatus.RUNNING
        task.started_at = task.started_at or datetime.now(timezone.utc)
        self.memory.log_event("task.running", {"task_id": task.id})

        try:
            if task.module_id:
                mod = self._resolve_module(task.module_id)
                if mod:
                    if task.module_id.lower() == "t3mp3st":
                        # Use the safety-hardened T3MP3ST MCP adapter
                        from sahiixx_agency.adapters.security.t3mp3st_mcp import T3mp3stMcpAdapter

                        t3mp3st_adapter = T3mp3stMcpAdapter(
                            clone_base_dir=os.path.join(self.config.data_dir, "repos"),
                            approval_token=self.config.t3mp3st_approval_token,
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
                        )
                        run_result = await hiring_adapter.run(mod, task.payload)
                        task.result = {
                            "module": mod.name,
                            "category": mod.category.value,
                            "url": mod.url,
                            "capabilities": mod.capabilities,
                            "execution": run_result,
                        }
                    elif task.module_id.lower() == "html_anything":
                        from sahiixx_agency.adapters.design.html_anything_adapter import HtmlAnythingAdapter

                        html_payload = dict(task.payload)
                        html_payload.setdefault("brief", task.intent)
                        html_adapter = HtmlAnythingAdapter(
                            clone_base_dir=os.path.join(self.config.data_dir, "repos"),
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
                        )
                        run_result = await om_adapter.run(mod, task.payload)
                        task.result = {
                            "module": mod.name,
                            "category": mod.category.value,
                            "url": mod.url,
                            "capabilities": mod.capabilities,
                            "execution": run_result,
                        }
                    else:
                        # Generic clone-and-run path
                        run_result = await self.runner.run(
                            mod,
                            command=task.payload.get("command", "run"),
                            env=task.payload.get("env"),
                            timeout=task.payload.get("timeout", 60),
                        )
                        task.result = {
                            "module": mod.name,
                            "category": mod.category.value,
                            "url": mod.url,
                            "capabilities": mod.capabilities,
                            "execution": run_result,
                        }
                    self.registry.set_status(mod.id, ModuleStatus.ACTIVE)
                else:
                    task.result = {"note": "Module not found in registry."}
            else:
                # No specific module — try to run a category adapter
                category = task.category
                if category:
                    task.result = await self._run_category_adapter(category, task.payload)
                else:
                    task.result = {
                        "note": "No module or category matched.",
                        "intent": task.intent,
                    }

            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now(timezone.utc)
            self.memory.log_event("task.completed", {"task_id": task.id})
        except Exception as exc:
            task.status = TaskStatus.FAILED
            task.error = str(exc)
            self.memory.log_event("task.failed", {"task_id": task.id, "error": str(exc)})

    async def _run_category_adapter(self, category: RepoCategory, payload: dict[str, Any]) -> dict[str, Any]:
        """Run the best module from a category."""
        modules = self.registry.by_category(category)
        if not modules:
            return {"note": f"No modules in category {category.value}"}
        # Pick the one with the most stars
        best = max(modules, key=lambda m: m.stars)
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
            id=f"intel_{__import__('uuid').uuid4().hex[:8]}",
            report_type=report_type,  # type: ignore[arg-type]
            repos=repos,
            summary=f"Scout found {len(repos)} repos for type '{report_type}'.",
            raw_queries=queries,
        )
        self.memory.log_event("intel.scout", {"report_id": report.id, "type": report_type, "count": len(repos)})
        return report
