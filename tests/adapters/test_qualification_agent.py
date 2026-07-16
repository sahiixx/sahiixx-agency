"""Tests for the QualificationAgent (lead scoring / pipeline routing)."""

from __future__ import annotations

import pytest

from sahiixx_agency.adapters.qualification_agent import QualificationAgent


def _lead(message: str, **over) -> dict:
    payload = {
        "lead_id": "lead_test",
        "contact": {"name": "A. Rahman", "handle": "+9715xxxx", "channel": "whatsapp"},
        "message": message,
        "source": "nexus_whatsapp",
        "captured_at": "2026-07-16T09:12:00Z",
        "raw_ref": "nexus:ESTATE-4471",
    }
    payload.update(over)
    return payload


@pytest.mark.asyncio
async def test_scores_high_intent_buyer():
    agent = QualificationAgent()
    res = await agent.execute(_lead("I want to buy a 2BR in Marina, budget 1.2M, moving in 3 months"))
    assert res["lead_id"] == "lead_test"
    assert res["intent"] == "buy"
    assert res["budget_band"] == "0.75M_1.5M"
    assert res["timeline"] == "soon_0_3m"
    assert res["score"] >= 60
    assert res["decision"] == "qualified_pipeline_entry"
    assert res["status"] == "qualified"
    assert res["next"] == "route_to_geomatch"


@pytest.mark.asyncio
async def test_low_info_lead_is_nurture():
    agent = QualificationAgent()
    res = await agent.execute(_lead("tell me about dubai real estate"))
    assert res["intent"] == "info"
    assert res["score"] < 60
    assert res["decision"].startswith("nurture")
    assert res["confidence"] in ("low", "medium")


@pytest.mark.asyncio
async def test_sell_intent_routes_to_pipeline():
    agent = QualificationAgent()
    res = await agent.execute(_lead("I want to sell my villa in Arabian Ranches, value around 5M, flexible timeline"))
    assert res["intent"] == "sell"
    assert res["budget_band"] == "3M_10M"
    assert res["decision"] == "qualified_pipeline_entry"


@pytest.mark.asyncio
async def test_explicit_million_budget_parsed():
    agent = QualificationAgent()
    res = await agent.execute(_lead("Budget 2 million AED, I want to buy an apartment, ASAP"))
    assert res["budget_band"] == "1.5M_3M"
    assert res["timeline"] == "urgent_0_1m"
    assert res["segment"] == "end_user_buyer"
