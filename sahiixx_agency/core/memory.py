"""Simple memory/context store for the agency."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any


class AgencyMemory:
    """SQLite-backed memory with JSON fallback."""

    def __init__(self, data_dir: str = "./data", backend: str = "sqlite") -> None:
        self.data_dir = data_dir
        self.backend = backend
        os.makedirs(data_dir, exist_ok=True)
        if backend == "sqlite":
            self.db_path = os.path.join(data_dir, "memory.db")
            self._init_sqlite()
        else:
            self.json_path = os.path.join(data_dir, "memory.json")
            self._data: dict[str, Any] = {}
            self._load_json()

    def _init_sqlite(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT,
                    payload TEXT,
                    created_at TEXT
                )
                """
            )
            conn.commit()

    def _load_json(self) -> None:
        if os.path.exists(self.json_path):
            with open(self.json_path, encoding="utf-8") as f:
                self._data = json.load(f)

    def _save_json(self) -> None:
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, default=str)

    def set(self, key: str, value: Any) -> None:
        if self.backend == "sqlite":
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO memory (key, value, updated_at) VALUES (?, ?, ?)",
                    (key, json.dumps(value), datetime.now(timezone.utc).isoformat()),
                )
                conn.commit()
        else:
            self._data[key] = value
            self._save_json()

    def get(self, key: str, default: Any = None) -> Any:
        if self.backend == "sqlite":
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute("SELECT value FROM memory WHERE key = ?", (key,)).fetchone()
                return json.loads(row[0]) if row else default
        return self._data.get(key, default)

    def log_event(self, topic: str, payload: dict[str, Any]) -> None:
        if self.backend == "sqlite":
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO events (topic, payload, created_at) VALUES (?, ?, ?)",
                    (topic, json.dumps(payload), datetime.now(timezone.utc).isoformat()),
                )
                conn.commit()
        else:
            events = self._data.setdefault("events", [])
            events.append({"topic": topic, "payload": payload, "created_at": datetime.now(timezone.utc).isoformat()})
            self._save_json()

    def save_task(self, task_id: str, task_data: dict[str, Any]) -> None:
        """Persist task state so it survives process restarts."""
        if self.backend == "sqlite":
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS tasks (
                        task_id TEXT PRIMARY KEY,
                        value TEXT,
                        updated_at TEXT
                    )
                    """
                )
                conn.execute(
                    "INSERT OR REPLACE INTO tasks (task_id, value, updated_at) VALUES (?, ?, ?)",
                    (task_id, json.dumps(task_data), datetime.now(timezone.utc).isoformat()),
                )
                conn.commit()
        else:
            tasks = self._data.setdefault("tasks", {})
            tasks[task_id] = task_data
            self._save_json()

    def load_tasks(self) -> list[dict[str, Any]]:
        """Load all persisted task states."""
        if self.backend == "sqlite":
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS tasks (
                        task_id TEXT PRIMARY KEY,
                        value TEXT,
                        updated_at TEXT
                    )
                    """
                )
                rows = conn.execute("SELECT value FROM tasks").fetchall()
                return [json.loads(r[0]) for r in rows]
        return list(self._data.get("tasks", {}).values())

    def recent_events(self, topic: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        if self.backend == "sqlite":
            with sqlite3.connect(self.db_path) as conn:
                if topic:
                    rows = conn.execute(
                        "SELECT topic, payload, created_at FROM events WHERE topic = ? ORDER BY id DESC LIMIT ?",
                        (topic, limit),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT topic, payload, created_at FROM events ORDER BY id DESC LIMIT ?",
                        (limit,),
                    ).fetchall()
                return [{"topic": r[0], "payload": json.loads(r[1]), "created_at": r[2]} for r in rows]
        events: list[dict[str, Any]] = self._data.get("events", [])
        if topic:
            events = [e for e in events if e.get("topic") == topic]
        return events[-limit:]
