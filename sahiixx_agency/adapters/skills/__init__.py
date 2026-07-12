from __future__ import annotations

from sahiixx_agency.adapters.base import BaseAdapter
from sahiixx_agency.adapters.skills.gcc_outbound import GccOutboundSkillAdapter


class SkillsAdapter(BaseAdapter):
    """Router adapter that selects a skill sub-adapter by intent/skill name."""

    def __init__(self, module: object | None = None) -> None:
        self.module = module
        self._gcc = GccOutboundSkillAdapter(module)

    async def execute(self, payload: dict[str, object]) -> dict[str, object]:
        skill = payload.get("skill", "gcc_outbound_prospecting")
        if skill.startswith("gcc_"):
            return await self._gcc.execute(payload)
        raise ValueError(f"Unknown skill: {skill}")
