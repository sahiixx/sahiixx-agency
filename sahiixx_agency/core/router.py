"""Task router — matches intents to the best agency module."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from .bus import BusMessage, MessageBus
from .models import AgencyTask, RepoCategory, RepoNode, TaskStatus
from .registry import RepoRegistry


class TaskRouter:
    """Routes tasks to modules using keyword matching + category hints."""

    def __init__(self, registry: RepoRegistry, bus: MessageBus) -> None:
        self.registry = registry
        self.bus = bus

    async def route(self, intent: str, payload: dict[str, Any] | None = None) -> AgencyTask:
        """Create and route a task to the best matching module(s)."""
        task = AgencyTask(
            id=f"task_{uuid.uuid4().hex[:12]}",
            intent=intent,
            payload=payload or {},
        )
        candidates = self._score_modules(intent)
        if candidates:
            best = candidates[0]
            task.module_id = best.id
            task.category = best.category
        else:
            task.category = self._infer_category(intent)

        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now(timezone.utc)

        await self.bus.publish(
            BusMessage(
                id=f"msg_{uuid.uuid4().hex[:8]}",
                topic=f"task.{task.status.value}",
                sender="router",
                payload={"task": task.model_dump(mode="json")},
                correlation_id=task.id,
            ),
        )
        return task

    def _score_modules(self, intent: str) -> list[RepoNode]:
        """Score all modules by relevance to the intent."""
        words = set(intent.lower().split())
        scored: list[tuple[float, RepoNode]] = []
        for mod in self.registry.modules:
            if mod.status.value in ("error", "inactive"):
                continue
            score = 0.0
            text = f"{mod.name} {mod.description or ''} {' '.join(mod.capabilities)}".lower()
            for word in words:
                if word in text:
                    score += 1.0
                if word in (mod.name or "").lower():
                    score += 2.0
            if mod.stars > 0:
                score += min(mod.stars / 1000, 3.0)
            if mod.category != RepoCategory.UNCATEGORIZED:
                score += 0.5
            scored.append((score, mod))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [mod for _, mod in scored if _ > 0]

    def _infer_category(self, intent: str) -> RepoCategory:
        intent_lower = intent.lower()
        for category, keywords in [
            (RepoCategory.VOICE_AI, ["voice", "speech", "audio", "call", "phone"]),
            (RepoCategory.REAL_ESTATE, ["property", "real estate", "dubai", "lead", "deal"]),
            (RepoCategory.SECURITY, ["security", "audit", "pentest", "cve", "scan"]),
            (RepoCategory.AGENT_FRAMEWORK, ["agent", "llm", "ai", "swarm", "bot"]),
            (RepoCategory.MCP_TOOL, ["tool", "mcp", "workflow", "automation"]),
            (RepoCategory.COOKBOOK, ["prompt", "template", "cookbook"]),
            (RepoCategory.OS_PLATFORM, ["os", "platform", "desktop"]),
        ]:
            if any(kw in intent_lower for kw in keywords):
                return category
        return RepoCategory.UNCATEGORIZED
