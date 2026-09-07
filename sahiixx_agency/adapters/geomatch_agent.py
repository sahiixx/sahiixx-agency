"""GeoMatchAgent: attaches area/property matches to a qualified lead.

Consumes ``LeadQualified`` (or a minimal payload with area/budget signals)
and returns a ``LeadMatched`` result with 3–10 candidate areas/listings.
Uses a curated Dubai area catalogue offline; can be extended to live inventory
via adapters/realestate/ later.

Payload (LeadQualified-compatible):
    lead_id, budget_band, intent, timeline, message (optional), area_hint (optional)

Returns (LeadMatched):
    lead_id, matches[], count, status, next
"""

from __future__ import annotations

from typing import Any

from sahiixx_agency.adapters.base import BaseAdapter

# Curated Dubai areas with rough AED mid-band and tags.
# Not a live inventory — a deterministic matching prior for E2E / offline use.
_DUBAI_AREAS: list[dict[str, Any]] = [
    {"area": "Dubai Marina", "mid_aed": 1_400_000, "tags": ["waterfront", "apartment", "investor"], "communities": ["Marina Gate", "Pier 7"]},
    {"area": "JLT", "mid_aed": 1_100_000, "tags": ["apartment", "metro", "value"], "communities": ["Cluster A", "Cluster X"]},
    {"area": "Business Bay", "mid_aed": 1_500_000, "tags": ["apartment", "canal", "city"], "communities": ["Executive Towers"]},
    {"area": "Downtown Dubai", "mid_aed": 2_200_000, "tags": ["luxury", "apartment", "landmark"], "communities": ["Boulevard Point"]},
    {"area": "Palm Jumeirah", "mid_aed": 4_500_000, "tags": ["luxury", "villa", "waterfront"], "communities": ["Frond G"]},
    {"area": "Arabian Ranches", "mid_aed": 2_800_000, "tags": ["villa", "family", "suburban"], "communities": ["Rancho"]},
    {"area": "Dubai Hills Estate", "mid_aed": 2_400_000, "tags": ["villa", "apartment", "family"], "communities": ["Hills Park"]},
    {"area": "JVC", "mid_aed": 900_000, "tags": ["value", "apartment", "family"], "communities": ["District 13"]},
    {"area": "Dubai Creek Harbour", "mid_aed": 1_800_000, "tags": ["waterfront", "apartment", "new"], "communities": ["Creek Gate"]},
    {"area": "City Walk", "mid_aed": 2_600_000, "tags": ["luxury", "apartment", "lifestyle"], "communities": ["The Residences"]},
]

_BUDGET_MID: dict[str, float] = {
    "0_750k": 500_000,
    "0.75M_1.5M": 1_100_000,
    "1.0M_1.5M": 1_250_000,
    "1.5M_3M": 2_200_000,
    "1.5M_2.5M": 2_000_000,
    "3M_10M": 5_000_000,
    "2.5M+": 3_500_000,
    "10M_plus": 12_000_000,
    "unknown": 1_500_000,
}


class GeoMatchAgent(BaseAdapter):
    """Attach area/property matches to a qualified lead."""

    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        lead_id = payload.get("lead_id")
        budget_band = str(payload.get("budget_band") or "unknown")
        intent = str(payload.get("intent") or "buy")
        message = str(payload.get("message") or "").lower()
        area_hint = str(payload.get("area_hint") or "").lower()

        # Pull area hints from free text if not explicit.
        if not area_hint:
            for a in _DUBAI_AREAS:
                if a["area"].lower() in message:
                    area_hint = a["area"].lower()
                    break
            for token in ("marina", "jlt", "downtown", "palm", "hills", "jvc", "creek", "bay"):
                if token in message:
                    area_hint = token
                    break

        target = _BUDGET_MID.get(budget_band, 1_500_000)

        scored: list[tuple[float, dict[str, Any]]] = []
        for area in _DUBAI_AREAS:
            score = 100.0 - abs(area["mid_aed"] - target) / max(target, 1) * 80.0
            # Intent affinity
            if intent == "rent" and "villa" in area["tags"]:
                score -= 10
            if intent == "buy" and "investor" in area["tags"]:
                score += 5
            # Hint boost
            if area_hint and (area_hint in area["area"].lower() or any(area_hint in t for t in area["tags"])):
                score += 25
            score = max(0.0, min(100.0, score))
            scored.append((score, area))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:8]
        matches = [
            {
                "area": a["area"],
                "score": round(s, 1),
                "mid_aed": a["mid_aed"],
                "tags": a["tags"],
                "sample_communities": a["communities"],
            }
            for s, a in top
            if s >= 30
        ][:10]

        status = "matched" if matches else "no_match"
        return {
            "lead_id": lead_id,
            "matches": matches,
            "count": len(matches),
            "budget_band": budget_band,
            "intent": intent,
            "status": status,
            "next": "route_to_scheduling" if status == "matched" else "route_to_nurture",
        }
