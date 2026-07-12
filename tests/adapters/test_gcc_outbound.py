from __future__ import annotations

import pytest

from sahiixx_agency.adapters.skills.gcc_outbound import GccOutboundSkillAdapter


@pytest.fixture
def adapter() -> GccOutboundSkillAdapter:
    return GccOutboundSkillAdapter(module=None)


@pytest.mark.asyncio
async def test_prospect(adapter: GccOutboundSkillAdapter) -> None:
    result = await adapter.execute({
        "skill": "gcc_outbound_prospecting",
        "context": {
            "prospect": {"name": "Ahmed", "company": "NoorTech", "role": "CTO", "country": "AE"},
            "our_company": {"name": "GulfAI", "value_prop": "AI-driven automation"},
            "signal": {"description": "hiring 5 senior AI engineers"},
        },
    })
    assert result["skill"] == "gcc_outbound_prospecting"
    assert "subject" in result
    assert "body" in result
    assert len(result["follow_ups"]) == 3


@pytest.mark.asyncio
async def test_real_estate_analyzer(adapter: GccOutboundSkillAdapter) -> None:
    result = await adapter.execute({
        "skill": "gcc_real_estate_deal_analyzer",
        "context": {
            "listing": {"title": "2BR in Dubai Hills", "price_aed": 2_000_000, "area_sqft": 1200, "bedrooms": 2, "handover_year": 2028, "country": "AE"},
            "purpose": "investment",
        },
    })
    assert result["skill"] == "gcc_real_estate_deal_analyzer"
    assert "metrics" in result
    assert 0 <= result["risk_score"] <= 100


@pytest.mark.asyncio
async def test_lead_scoring(adapter: GccOutboundSkillAdapter) -> None:
    result = await adapter.execute({
        "skill": "gcc_lead_scoring",
        "context": {
            "leads": [
                {"name": "Ali", "company": "X", "role": "CTO", "country": "SA", "signal": "hiring", "email": "ali@x.com"},
                {"name": "Sam", "company": "Y", "role": "Intern", "country": "US", "signal": ""},
            ],
            "icp": {"target_countries": ["SA", "AE"], "target_roles": ["cto", "vp"]},
            "max_results": 10,
        },
    })
    assert result["skill"] == "gcc_lead_scoring"
    assert len(result["scored_leads"]) == 2
    assert result["scored_leads"][0]["score"] >= result["scored_leads"][1]["score"]


@pytest.mark.asyncio
async def test_market_signals(adapter: GccOutboundSkillAdapter) -> None:
    result = await adapter.execute({
        "skill": "gcc_market_signals",
        "context": {"keywords": ["AI"], "countries": ["AE"], "categories": ["hiring"], "max_signals": 5},
    })
    assert result["skill"] == "gcc_market_signals"
    assert len(result["signals"]) == 5


@pytest.mark.asyncio
async def test_unknown_skill(adapter: GccOutboundSkillAdapter) -> None:
    with pytest.raises(ValueError, match="Unknown GCC outbound skill"):
        await adapter.execute({"skill": "gcc_unknown", "context": {}})
