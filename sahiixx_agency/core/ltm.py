"""Phase 2 autonomy scaffolding: long-term memory integration stub.

A real implementation would use a vector store (Qdrant, Chroma, etc.) for
embeddings and retrieval. This stub provides the interface and stores
summaries in AgencyMemory so the rest of the system can be wired up.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sahiixx_agency.core.memory import AgencyMemory


class LongTermMemory:
    """Stub long-term memory for cross-session context."""

    def __init__(self, memory: AgencyMemory) -> None:
        self.memory = memory

    def remember(
        self,
        content: str,
        topic: str = "general",
        source_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Store a memory and return its id."""
        memory_id = f"mem_{uuid.uuid4().hex[:8]}"
        self.memory.set(
            f"ltm:{memory_id}",
            {
                "id": memory_id,
                "topic": topic,
                "content": content,
                "source_id": source_id,
                "metadata": metadata or {},
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        index = self.memory.get("ltm:index", [])
        index.append(memory_id)
        self.memory.set("ltm:index", index)
        return memory_id

    def recall(
        self,
        query: str | None = None,
        topic: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Retrieve memories, optionally filtered by topic or query substring."""
        results = []
        for memory_id in self.memory.get("ltm:index", []):
            data = self.memory.get(f"ltm:{memory_id}")
            if not data:
                continue
            if topic and data.get("topic") != topic:
                continue
            if query and query.lower() not in data.get("content", "").lower():
                continue
            results.append(data)
        return results[:limit]

    def forget(self, memory_id: str) -> bool:
        """Remove a memory."""
        key = f"ltm:{memory_id}"
        if self.memory.get(key) is None:
            return False
        self.memory.set(key, None)
        index = self.memory.get("ltm:index", [])
        if memory_id in index:
            index.remove(memory_id)
            self.memory.set("ltm:index", index)
        return True
