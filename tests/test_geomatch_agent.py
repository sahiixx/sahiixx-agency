"""Unit tests for GeoMatchAgent (offline, no network)."""

from __future__ import annotations

import asyncio

from sahiixx_agency.adapters.geomatch_agent import GeoMatchAgent


def _run(payload: dict):
    agent = GeoMatchAgent()
    return asyncio.get_event_loop().run_until_complete(agent.execute(payload))


def test_marina_hint_ranks_marina_high():
    result = _run(
        {
            "lead_id": "lead_test_1",
            "budget_band": "1.0M_1.5M",
            "intent": "buy",
            "message": "Looking for a 2BR in Marina, budget 1.2M",
        }
    )
    assert result["status"] == "matched"
    assert result["count"] >= 1
    areas = [m["area"] for m in result["matches"]]
    assert "Dubai Marina" in areas
    assert result["next"] == "route_to_scheduling"


def test_unknown_budget_still_returns_matches():
    result = _run({"lead_id": "lead_x", "budget_band": "unknown", "intent": "info"})
    assert result["count"] >= 1
    assert "matches" in result


def test_empty_payload_safe():
    result = _run({})
    assert "matches" in result
    assert result["status"] in ("matched", "no_match")
