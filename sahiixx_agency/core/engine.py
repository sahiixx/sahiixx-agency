"""Main orchestration engine — wires registry, bus, router, memory together."""

from __future__ import annotations

import asyncio
import contextlib
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from .bus import MessageBus
from .memory import AgencyMemory
from .models import (
    AgencyConfig,
    AgencyTask,
    IntelReport,
    ModuleStatus,
    RepoCategory,
    RepoNode,
    TaskStatus,
)
from .registry import RepoRegistry
from .router import TaskRouter
from .runner import CloneManager, RepoRunner

_STOP_SENTINEL = object()


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
        self._worker_task: asyncio.Task[None] | None = None
        self._tasks: dict[str, AgencyTask] = {}
        self._task_queue: asyncio.Queue[AgencyTask] = asyncio.Queue()
        self._scheduler_running = False
        self._scheduler_task: asyncio.Task[None] | None = None
        self._scheduler_interval_minutes: float = max(0, self.config.auto_sync_interval_minutes)
        self._last_sync_at: datetime | None = None
        self._next_sync_at: datetime | None = None

    async def sync_repos(self, username: str | None = None) -> list[RepoNode]:
        """Sync all GitHub repos into the registry."""
        user = username or self.config.github_username
        discovered = await self.registry.discover(user)
        self.memory.log_event("registry.sync", {"username": user, "count": len(discovered)})
        return discovered

    async def dispatch(self, intent: str, payload: dict[str, Any] | None = None) -> AgencyTask:
        """Dispatch a task through the agency synchronously."""
        task = await self.router.route(intent, payload)
        self._tasks[task.id] = task
        self.memory.log_event("task.created", {"task_id": task.id, "intent": intent})
        await self._execute_task(task)
        return task

    async def submit_task(
        self,
        intent: str,
        payload: dict[str, Any] | None = None,
        module_id: str | None = None,
        category: RepoCategory | None = None,
    ) -> AgencyTask:
        """Submit a task to the background worker queue.

        The task is created in ``PENDING`` state and processed asynchronously by
        the worker. Routing is resolved immediately so callers can track the
        chosen module/category. Explicit ``module_id`` / ``category`` hints
        override the router's choice when provided.
        """
        routed = await self.router.route(intent, payload or {})
        task = AgencyTask(
            id=routed.id,
            intent=routed.intent,
            module_id=module_id or routed.module_id,
            category=category or routed.category,
            payload=routed.payload,
            status=TaskStatus.PENDING,
        )
        self._tasks[task.id] = task
        self.memory.log_event("task.created", {"task_id": task.id, "intent": intent})
        await self._task_queue.put(task)
        return task

    async def start_worker(self) -> None:
        """Start the background task worker."""
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._task_worker())

    async def stop_worker(self) -> None:
        """Stop the background task worker."""
        if not self._running:
            return
        self._running = False
        await self._task_queue.put(_STOP_SENTINEL)  # type: ignore[arg-type]
        if self._worker_task is not None:
            with contextlib.suppress(asyncio.CancelledError):
                await self._worker_task
            self._worker_task = None

    async def start_scheduler(self, interval_minutes: float | None = None) -> None:
        """Start the background registry auto-sync scheduler.

        If ``interval_minutes`` is provided it overrides the config value.
        A value of ``0`` disables scheduled sync.
        """
        if interval_minutes is not None:
            self._scheduler_interval_minutes = max(0.0, interval_minutes)
        if self._scheduler_running:
            return
        if self._scheduler_interval_minutes <= 0:
            return
        self._scheduler_running = True
        self._next_sync_at = datetime.now(UTC) + timedelta(minutes=self._scheduler_interval_minutes)
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

    async def stop_scheduler(self) -> None:
        """Stop the background registry auto-sync scheduler."""
        if not self._scheduler_running:
            return
        self._scheduler_running = False
        if self._scheduler_task is not None:
            with contextlib.suppress(asyncio.CancelledError):
                self._scheduler_task.cancel()
                await self._scheduler_task
            self._scheduler_task = None

    async def _scheduler_loop(self) -> None:
        """Background loop that syncs the registry on a schedule."""
        while self._scheduler_running:
            self._next_sync_at = datetime.now(UTC) + timedelta(minutes=self._scheduler_interval_minutes)
            await asyncio.sleep(self._scheduler_interval_minutes * 60)
            if not self._scheduler_running:
                break
            try:
                await self.sync_repos(self.config.github_username)
                self._last_sync_at = datetime.now(UTC)
            except Exception as exc:  # pragma: no cover - logged, not fatal
                self.memory.log_event("scheduler.sync_failed", {"error": str(exc)})

    def scheduler_status(self) -> dict[str, Any]:
        """Return current scheduler state."""
        return {
            "running": self._scheduler_running,
            "interval_minutes": self._scheduler_interval_minutes,
            "last_sync_at": self._last_sync_at.isoformat() if self._last_sync_at else None,
            "next_sync_at": self._next_sync_at.isoformat() if self._next_sync_at else None,
        }

    async def _task_worker(self) -> None:
        """Background loop that pulls tasks from the queue and executes them."""
        while self._running:
            task = await self._task_queue.get()
            if task is _STOP_SENTINEL:
                self._task_queue.task_done()
                break

            task.status = TaskStatus.RUNNING
            task.started_at = task.started_at or datetime.now(UTC)

            try:
                await self._execute_task(task)
            except Exception as exc:
                task.status = TaskStatus.FAILED
                task.error = str(exc)
                task.completed_at = datetime.now(UTC)
                self.memory.log_event("task.failed", {"task_id": task.id, "error": str(exc)})
            finally:
                self._task_queue.task_done()

    def get_task(self, task_id: str) -> AgencyTask | None:
        """Return a submitted task by ID."""
        return self._tasks.get(task_id)

    def list_tasks(self, limit: int = 50) -> list[AgencyTask]:
        """Return recent tasks ordered by creation time (newest first)."""
        sorted_tasks = sorted(self._tasks.values(), key=lambda t: t.created_at, reverse=True)
        return sorted_tasks[:limit]

    @property
    def worker_running(self) -> bool:
        """Whether the background task worker is running."""
        return self._running

    @property
    def queue_size(self) -> int:
        """Current number of tasks waiting in the queue."""
        return self._task_queue.qsize()

    async def _execute_task(self, task: AgencyTask) -> None:
        """Execute a task by cloning and running the target module."""
        task.status = TaskStatus.RUNNING
        task.started_at = task.started_at or datetime.now(UTC)
        self.memory.log_event("task.running", {"task_id": task.id})

        try:
            if task.module_id:
                mod = self.registry.get(task.module_id)
                if mod:
                    # Actually clone and run the module
                    run_result = await self.runner.run(
                        mod,
                        command=task.payload.get("command", "run"),
                        env=task.payload.get("env"),
                        timeout=task.payload.get("timeout", 60),
                        skip_install=task.payload.get("skip_install", False),
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
            task.completed_at = datetime.now(UTC)
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
            skip_install=payload.get("skip_install", False),
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
        from datetime import datetime

        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "sahiixx-agency",
        }
        if self.config.github_token:
            headers["Authorization"] = f"Bearer {self.config.github_token}"

        repos: list[RepoNode] = []
        queries: list[str] = []

        async with __import__("httpx").AsyncClient(timeout=30) as client:
            if report_type in ("trending", "velocity"):
                week_ago = (datetime.now(UTC) - timedelta(days=7)).strftime("%Y-%m-%d")
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
        self.memory.log_event(
            "intel.scout",
            {"report_id": report.id, "type": report_type, "count": len(repos)},
        )
        return report
