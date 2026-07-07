"""Phase 2 autonomy scaffolding: scheduled workflow daemon.

This is intentionally lightweight. A production scheduler would use APScheduler,
Celery Beat, or a separate worker process. The scaffold provides the interface
and persistence hooks so the agency can trigger recurring workflows.
"""

from __future__ import annotations

import asyncio
import uuid
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any


@dataclass
class ScheduledWorkflow:
    """A recurring workflow schedule."""

    id: str = field(default_factory=lambda: f"sched_{uuid.uuid4().hex[:8]}")
    workflow_id: str = ""
    interval_seconds: int = 3600
    payload: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def compute_next(self, base: datetime | None = None) -> datetime:
        """Compute the next run time from the interval."""
        base = base or datetime.now(timezone.utc)
        return base + timedelta(seconds=self.interval_seconds)


class WorkflowScheduler:
    """In-memory scheduler scaffold for recurring workflows.

    Persists schedules via the agency memory backend and exposes a simple
    polling loop that can be run as a background task.
    """

    def __init__(self, engine: Any, poll_interval_seconds: float = 60.0) -> None:
        self.engine = engine
        self.poll_interval_seconds = poll_interval_seconds
        self._schedules: dict[str, ScheduledWorkflow] = {}
        self._running = False
        self._task: asyncio.Task[Any] | None = None

    def _memory_key(self, schedule_id: str) -> str:
        return f"workflow_schedule:{schedule_id}"

    def load_schedules(self) -> None:
        """Load persisted schedules from memory."""
        index = self.engine.memory.get("workflow_schedules:index", [])
        self._schedules = {}
        for sid in index:
            data = self.engine.memory.get(self._memory_key(sid))
            if data:
                try:
                    schedule = ScheduledWorkflow(**data)
                    self._schedules[schedule.id] = schedule
                except Exception:
                    continue

    def save_schedule(self, schedule: ScheduledWorkflow) -> None:
        """Persist a schedule and update the index."""
        if schedule.next_run_at is None:
            schedule.next_run_at = schedule.compute_next()
        self._schedules[schedule.id] = schedule
        self.engine.memory.set(self._memory_key(schedule.id), {
            "id": schedule.id,
            "workflow_id": schedule.workflow_id,
            "interval_seconds": schedule.interval_seconds,
            "payload": schedule.payload,
            "enabled": schedule.enabled,
            "last_run_at": schedule.last_run_at.isoformat() if schedule.last_run_at else None,
            "next_run_at": schedule.next_run_at.isoformat() if schedule.next_run_at else None,
            "created_at": schedule.created_at.isoformat(),
        })
        index = list(self._schedules.keys())
        self.engine.memory.set("workflow_schedules:index", index)

    def delete_schedule(self, schedule_id: str) -> bool:
        """Remove a schedule."""
        if schedule_id not in self._schedules:
            return False
        del self._schedules[schedule_id]
        index = list(self._schedules.keys())
        self.engine.memory.set("workflow_schedules:index", index)
        return True

    def list_schedules(self) -> list[ScheduledWorkflow]:
        """Return all schedules."""
        return list(self._schedules.values())

    async def start(self) -> None:
        """Start the scheduler polling loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        """Stop the scheduler polling loop."""
        if not self._running:
            return
        self._running = False
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _loop(self) -> None:
        while self._running:
            try:
                await self._tick()
            except Exception as exc:
                self.engine.memory.log_event("scheduler.error", {"error": str(exc)})
            await asyncio.sleep(self.poll_interval_seconds)

    async def _tick(self) -> None:
        now = datetime.now(timezone.utc)
        for schedule in list(self._schedules.values()):
            if not schedule.enabled or not schedule.next_run_at:
                continue
            if schedule.next_run_at <= now:
                await self._trigger(schedule)

    async def _trigger(self, schedule: ScheduledWorkflow) -> None:
        """Run the scheduled workflow."""
        try:
            instance = self.engine.workflows.create_instance(schedule.workflow_id, schedule.payload)
            if instance is not None:
                await self.engine.workflows.run_instance(instance.id)
            else:
                self.engine.memory.log_event(
                    "scheduler.workflow_failed",
                    {"schedule_id": schedule.id, "workflow_id": schedule.workflow_id, "error": "definition not found or disabled"},
                )
        except Exception as exc:
            self.engine.memory.log_event(
                "scheduler.workflow_failed",
                {"schedule_id": schedule.id, "workflow_id": schedule.workflow_id, "error": str(exc)},
            )
        finally:
            schedule.last_run_at = datetime.now(timezone.utc)
            schedule.next_run_at = schedule.compute_next(schedule.last_run_at)
            self.save_schedule(schedule)
            self.engine.audit.log(
                "scheduler.triggered",
                "scheduler",
                schedule.workflow_id,
                {"schedule_id": schedule.id},
            )
