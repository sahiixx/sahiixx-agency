"""Chat thread storage and command-center conversation handling."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sahiixx_agency.core.models import ChatMessage, ChatThread, MessageRole


class ChatManager:
    """In-memory store for agency chat threads and messages.

    Threads are keyed by a short uuid and kept in memory only for the runtime
    of the engine. Persistence can be added later via the memory backend.
    """

    def __init__(self) -> None:
        self._threads: dict[str, ChatThread] = {}

    def create_thread(self, title: str | None = None) -> ChatThread:
        """Create a new empty thread."""
        thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        thread = ChatThread(id=thread_id, title=title or f"Thread {thread_id}")
        self._threads[thread_id] = thread
        return thread

    def get_thread(self, thread_id: str) -> ChatThread | None:
        """Return a thread by id, or None if unknown."""
        return self._threads.get(thread_id)

    def list_threads(self, limit: int = 50) -> list[ChatThread]:
        """Return threads ordered by most recently updated."""
        sorted_threads = sorted(
            self._threads.values(),
            key=lambda t: t.updated_at,
            reverse=True,
        )
        return sorted_threads[:limit]

    def add_message(
        self,
        thread_id: str,
        role: MessageRole,
        content: str,
        task_id: str | None = None,
    ) -> ChatMessage:
        """Add a message to a thread, creating the thread if needed."""
        thread = self._threads.get(thread_id)
        if thread is None:
            thread = self.create_thread(title=f"Thread {thread_id}")
            # Honor the caller's id if one was supplied.
            thread.id = thread_id
            self._threads[thread_id] = thread

        message = ChatMessage(
            id=f"msg_{uuid.uuid4().hex[:8]}",
            role=role,
            content=content,
            task_id=task_id,
        )
        thread.messages.append(message)
        now = datetime.now(timezone.utc)
        thread.updated_at = now
        return message

    def delete_thread(self, thread_id: str) -> bool:
        """Delete a thread. Returns True if it existed."""
        return self._threads.pop(thread_id, None) is not None

    def to_dict(self) -> dict[str, Any]:
        """Serialize all threads for basic memory export."""
        return {
            thread_id: thread.model_dump(mode="json")
            for thread_id, thread in self._threads.items()
        }
