"""Voice AI adapter — clones and runs voice repos."""

from __future__ import annotations

from typing import Any

from sahiixx_agency.core.models import RepoNode
from sahiixx_agency.adapters.base import BaseAdapter


class VoiceAdapter(BaseAdapter):
    """Adapter for voice AI repos."""

    async def run(self, module: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
        payload.setdefault("timeout", 90)
        return await super().run(module, payload)


def run_voice_module(module: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
    import asyncio

    adapter = VoiceAdapter()
    return asyncio.run(adapter.run(module, payload))
