"""Task router - matches intents to the best agency module."""

from __future__ import annotations

import re
import uuid
from typing import Any

from .bus import MessageBus
from .models import AgencyConfig, AgencyTask, BusMessage, RepoCategory, RepoNode, RoutingRule, TaskStatus
from .registry import RepoRegistry


class TaskRouter:
    """Routes tasks to modules using config-driven rules then keyword scoring.

    Priority:
    1. ``routing_rules`` from AgencyConfig (regex pattern matched against intent)
       -> target is resolved via the ``ecosystem`` registry in config.
    2. Keyword/scoring fallback against all registered RepoNode modules.
    """

    def __init__(
        self,
        registry: RepoRegistry,
        bus: MessageBus,
        config: AgencyConfig | None = None,
    ) -> None:
        self.registry = registry
        self.bus = bus
        self.config = config or AgencyConfig()
        # Pre-compile routing rule patterns for efficiency
        self._compiled_rules: list[tuple[re.Pattern[str], RoutingRule]] = [
            (re.compile(rule.pattern, re.IGNORECASE), rule) for rule in self.config.routing_rules
        ]

    async def route(self, intent: str, payload: dict[str, Any] | None = None) -> AgencyTask:
        """Create and route a task to the best matching module."""
        task = AgencyTask(
            id=f"task_{uuid.uuid4().hex[:12]}",
            intent=intent,
            payload=payload or {},
        )

        # 1. Try config-driven routing_rules first
        module = self._match_routing_rules(intent)
        if module:
            task.module_id = module.id
            task.category = module.category
        else:
            # 2. Fallback to keyword scoring across registry
            candidates = self._score_modules(intent)
            if candidates:
                best = candidates[0]
                task.module_id = best.id
                task.category = best.category
            else:
                task.category = self._infer_category(intent)

        task.status = TaskStatus.PENDING

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

    def _match_routing_rules(self, intent: str) -> RepoNode | None:
        """Match intent against config routing_rules; return the target RepoNode if found.

        The target key in each rule refers to a key in ``config.ecosystem``.
        The ecosystem entrys ``repo`` field is used to look up the registry module.
        When the registry has not yet been synced, falls back to a stub RepoNode
        built from the ecosystem entry so routing metadata is still propagated.
        """
        for pattern, rule in self._compiled_rules:
            if pattern.search(intent):
                return self._resolve_ecosystem_target(rule.target)
        return None

    def _resolve_ecosystem_target(self, target_key: str) -> RepoNode | None:
        """Resolve an ecosystem key to a RepoNode.

        Lookup order:
        1. config.ecosystem[target_key]["repo"] -> registry module by that repo name.
        2. Direct registry lookup by target_key itself (matches when repo name == key).
        3. Stub RepoNode built from the ecosystem entry (pre-sync fallback).
        """
        eco = self.config.ecosystem.get(target_key)
        if eco:
            repo_name = eco.get("repo", target_key)
            node = self.registry.get(repo_name)
            if node is None:
                node = self.registry.get(target_key)
            if node is not None:
                # Merge ecosystem adapter_config into the synced node so
                # agency.yaml settings (blocked_targets, allow_local, etc.)
                # are applied to already-synced modules.
                eco_adapter_config = eco.get("adapter_config")
                if eco_adapter_config:
                    merged = {**node.adapter_config, **eco_adapter_config}
                    return node.model_copy(update={"adapter_config": merged})
                return node
            # Build a lightweight stub so routing metadata is available.
            # Use the ecosystem key as the node id so downstream lookups
            # (e.g. in AgencyEngine) match registry entries keyed by id.
            owner = eco.get("owner", "sahiixx")
            return RepoNode(
                id=target_key,
                name=repo_name,
                owner=owner,
                full_name=f"{owner}/{repo_name}",
                url=eco.get("url", f"https://github.com/{owner}/{repo_name}"),
                description=eco.get("role"),
                adapter_config=eco.get("adapter_config", {}),
            )
        # Direct registry lookup as final fallback
        return self.registry.get(target_key)

    def _score_modules(self, intent: str) -> list[RepoNode]:
        """Score all modules by relevance to the intent."""
        words = set(intent.lower().split())
        scored: list[tuple[float, RepoNode]] = []
        for mod in self.registry.modules:
            if mod.status.value in ("error", "inactive"):
                continue
            score = 0.0
            parts = [mod.name, mod.description or "", *mod.capabilities]
            text = " ".join(parts).lower()
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
