"""Security adapter — clones and runs security repos."""

from __future__ import annotations

from typing import Any

from sahiixx_agency.adapters.base import BaseAdapter
from sahiixx_agency.core.models import RepoNode


class SecurityAdapter(BaseAdapter):
    """Adapter for security repos."""

    async def run(self, module: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
        payload.setdefault("timeout", 180)
        return await super().run(module, payload)


def run_security_module(module: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
    import asyncio

    adapter = SecurityAdapter()
    return asyncio.run(adapter.run(module, payload))
