"""Real estate adapter — clones and runs real estate repos."""

from __future__ import annotations

from typing import Any

from sahiixx_agency.adapters.base import BaseAdapter
from sahiixx_agency.core.models import RepoNode


class RealEstateAdapter(BaseAdapter):
    """Adapter for real estate repos."""

    async def run(self, module: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
        payload.setdefault("timeout", 120)
        return await super().run(module, payload)


def run_realestate_module(module: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
    import asyncio

    adapter = RealEstateAdapter()
    return asyncio.run(adapter.run(module, payload))
