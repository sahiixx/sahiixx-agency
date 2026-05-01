"""Agent framework adapter — clones and runs agent repos."""

from __future__ import annotations

from typing import Any

from sahiixx_agency.core.models import RepoNode
from sahiixx_agency.adapters.base import BaseAdapter


class AgentAdapter(BaseAdapter):
    """Adapter for agent-framework repos."""

    async def run(self, module: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
        payload.setdefault("timeout", 120)
        return await super().run(module, payload)


def run_agent_module(module: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
    """Synchronous wrapper for agent module execution."""
    import asyncio

    adapter = AgentAdapter()
    return asyncio.run(adapter.run(module, payload))
