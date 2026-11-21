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


@pytest.mark.asyncio
@pytest.mark.parametrize("unit", ["M", "mn", "MN", "million"])
async def test_million_units_have_equivalent_budget_bands(unit, tmp_path):
    agent = QualificationAgent(clone_base_dir=str(tmp_path / "repos"))
    res = await agent.execute(_lead(f"I want to buy in Marina, budget AED 1.2{unit}, ASAP"))
    assert res["budget_band"] == "0.75M_1.5M"


@pytest.mark.asyncio
async def test_whatsapp_capture_to_qualification_preserves_identity(tmp_path):
    from sahiixx_agency.adapters.lead_capture_agent import LeadCaptureAgent

    clone_dir = str(tmp_path / "repos")
    captured = await LeadCaptureAgent(clone_base_dir=clone_dir).execute(
        {
            "lead_id": "lead_fixture",
            "wa_id": "fixture_contact",
            "message_id": "fixture_message",
            "message": "I want to buy in Marina, budget AED 1.2mn, ASAP",
            "source": "nexus_whatsapp",
        }
    )
    qualified = await QualificationAgent(clone_base_dir=clone_dir).execute(captured)

    assert captured["event"] == "lead.created"
    assert captured["contact"]["channel"] == "whatsapp"
    assert captured["raw_ref"] == "fixture_message"
    assert qualified["lead_id"] == captured["lead_id"] == "lead_fixture"
    assert qualified["budget_band"] == "0.75M_1.5M"
    assert qualified["status"] == "qualified"
    assert qualified["next"] == "route_to_geomatch"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("phrase", "expected"),
    [
        ("in 1 month", "urgent_0_1m"),
        ("next month", "urgent_0_1m"),
        ("in 3 months", "soon_0_3m"),
        ("in 1.5 months", "soon_0_3m"),
        ("in 12 weeks", "soon_0_3m"),
        ("in 6 months", "exploratory"),
        ("in 12 months", "exploratory"),
        ("in 24 months", "exploratory"),
        ("in 2 years", "exploratory"),
        ("in 0.5 years", "exploratory"),
        ("a monthly newsletter", "unknown"),
        ("Q4", "unknown"),
        ("some months later", "unknown"),
    ],
)
async def test_timeline_uses_complete_duration(phrase, expected, tmp_path):
    agent = QualificationAgent(clone_base_dir=str(tmp_path / "repos"))
    result = await agent.execute(_lead(f"I want to buy, {phrase}"))
    assert result["timeline"] == expected


@pytest.mark.asyncio
async def test_exploratory_lead_without_budget_is_not_qualified(tmp_path):
    agent = QualificationAgent(clone_base_dir=str(tmp_path / "repos"))
    result = await agent.execute(_lead("I want to buy someday, just exploring"))
    assert result["score"] == 30
    assert result["status"] != "qualified"
    assert result["next"] == "route_to_nurture"
    assert any("+0" in item for item in result["rationale"])


@pytest.mark.asyncio
async def test_missing_timeline_caps_confidence(tmp_path):
    agent = QualificationAgent(clone_base_dir=str(tmp_path / "repos"))
    result = await agent.execute(_lead("I want to buy, budget 1.2M"))
    assert result["timeline"] == "unknown"
    assert result["confidence"] == "low"
