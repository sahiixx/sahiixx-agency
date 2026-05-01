"""MCP tool adapter — clones and runs MCP/tool repos."""

from __future__ import annotations

from typing import Any

from sahiixx_agency.core.models import RepoNode
from sahiixx_agency.adapters.base import BaseAdapter


class McpAdapter(BaseAdapter):
    """Adapter for MCP/tool repos."""

    async def run(self, module: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
        payload.setdefault("timeout", 90)
        return await super().run(module, payload)


def run_mcp_module(module: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
    import asyncio

    adapter = McpAdapter()
    return asyncio.run(adapter.run(module, payload))
