"""Hiring-Agent adapter package."""

from sahiixx_agency.adapters.hiring.hiring_agent_adapter import (
    HiringAgentAdapter,
    HiringAgentResult,
    evaluate_resume,
)

__all__ = ["HiringAgentAdapter", "HiringAgentResult", "evaluate_resume"]
