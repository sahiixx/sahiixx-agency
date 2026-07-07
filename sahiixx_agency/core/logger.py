"""Structured JSON line logger for per-task observability."""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]


class TaskLogger:
    """Append-only JSONL logger for task lifecycle events.

    Each task gets its own ``{task_id}.jsonl`` file under
    ``{data_dir}/task-logs``.  File I/O is offloaded to a worker thread
    via ``asyncio.to_thread`` so async callers do not block the event loop.
    """

    def __init__(self, data_dir: str | os.PathLike[str]) -> None:
        self.data_dir = Path(data_dir)
        self.log_dir = self.data_dir / "task-logs"

    def _ensure_log_dir(self) -> None:
        """Create the log directory on first write."""
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _log_path(self, task_id: str) -> Path:
        """Return the JSONL path for a task."""
        return self.log_dir / f"{task_id}.jsonl"

    @staticmethod
    def _serialize_extra(extra: dict[str, Any]) -> dict[str, Any]:
        """Recursively convert ``extra`` values to JSON-serializable forms.

        * ``datetime`` instances become ISO-8601 strings.
        * Nested ``dict``/``list`` structures are traversed.
        * Values that still cannot be serialized fall back to ``str(value)``.
        """

        def _convert(value: Any) -> Any:
            if isinstance(value, datetime):
                return value.isoformat()
            if isinstance(value, dict):
                return {k: _convert(v) for k, v in value.items()}
            if isinstance(value, (list, tuple)):
                return [_convert(v) for v in value]
            try:
                json.dumps(value)
                return value
            except (TypeError, ValueError):
                return str(value)

        return {k: _convert(v) for k, v in extra.items()}

    def _log_sync(
        self,
        task_id: str,
        level: str,
        message: str,
        actor: str,
        extra: dict[str, Any],
    ) -> dict[str, Any]:
        """Synchronous entry writer; runs inside ``asyncio.to_thread``."""
        self._ensure_log_dir()
        entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level.upper(),
            "task_id": task_id,
            "actor": actor,
            "message": message,
            "extra": extra,
        }
        path = self._log_path(task_id)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    async def log(
        self,
        task_id: str,
        level: str,
        message: str,
        actor: str = "system",
        **extra: Any,
    ) -> dict[str, Any]:
        """Append a structured log entry for ``task_id``.

        Args:
            task_id: Unique task identifier.
            level: Standard Python logging level name (e.g. ``INFO``).
            message: Human-readable log message.
            actor: Short actor name such as ``engine``, ``approval``, ``chat``,
                ``api``, or ``system``.
            **extra: Arbitrary context; non-serializable values are converted.

        Returns:
            The log entry that was written.
        """
        safe_extra = self._serialize_extra(extra) if extra else {}
        return await asyncio.to_thread(
            self._log_sync, task_id, level, message, actor, safe_extra
        )

    async def info(
        self,
        task_id: str,
        message: str,
        actor: str = "system",
        **extra: Any,
    ) -> dict[str, Any]:
        """Convenience helper for INFO-level logs."""
        return await self.log(task_id, "INFO", message, actor=actor, **extra)

    async def warning(
        self,
        task_id: str,
        message: str,
        actor: str = "system",
        **extra: Any,
    ) -> dict[str, Any]:
        """Convenience helper for WARNING-level logs."""
        return await self.log(task_id, "WARNING", message, actor=actor, **extra)

    async def error(
        self,
        task_id: str,
        message: str,
        actor: str = "system",
        **extra: Any,
    ) -> dict[str, Any]:
        """Convenience helper for ERROR-level logs."""
        return await self.log(task_id, "ERROR", message, actor=actor, **extra)

    async def debug(
        self,
        task_id: str,
        message: str,
        actor: str = "system",
        **extra: Any,
    ) -> dict[str, Any]:
        """Convenience helper for DEBUG-level logs."""
        return await self.log(task_id, "DEBUG", message, actor=actor, **extra)

    def _read_sync(self, task_id: str) -> list[dict[str, Any]]:
        """Synchronous log reader; runs inside ``asyncio.to_thread``."""
        path = self._log_path(task_id)
        if not path.exists():
            return []
        entries: list[dict[str, Any]] = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    # Skip corrupt lines rather than crashing the reader.
                    continue
        return entries

    async def read(self, task_id: str) -> list[dict[str, Any]]:
        """Read all log entries for a task.

        Returns an empty list if the log file does not exist.  Corrupt JSON
        lines are skipped silently so the endpoint stays available.
        """
        return await asyncio.to_thread(self._read_sync, task_id)
