"""Qualification agent: scores a captured lead and decides pipeline entry.

This is the second specialist in the E2E lead machine (after LeadCapture).
It runs in-process via ``execute()`` and turns a ``LeadCreated`` payload
into a ``LeadQualified`` result: an intent/budget/timeline estimate, a 0–100
score, and a decision (pipeline entry / nurture / drop). All Tier-2
(financial/production) actions stay out of scope — this agent only reads
and scores, never books or offers.

Payload (LeadCreated from LeadCaptureAgent):
    lead_id:   str
    contact:    { name, handle, channel }
    message:    str  (free-text enquiry)
    source:     str  (e.g. "nexus_whatsapp")
    captured_at: str  (ISO timestamp)
    raw_ref:    str | None

Returns (LeadQualified):
    lead_id, score, segment, intent, timeline, budget_band,
    decision, confidence, rationale[], tags[], status, next
"""

from __future__ import annotations

import re
from typing import Any

from sahiixx_agency.adapters.base import BaseAdapter

_INTENT_PATTERNS: dict[str, str] = {
    "buy": r"\b(buy|purchase|own|invest|acquire|get (a|an) (apartment|villa|property|home))\b",
    "sell": r"\b(sell|list|offload|dispose|exit|liquidate)\b",
    "rent": r"\b(rent|lease|let|tenant|rental)\b",
    "info": r"\b(info|tell me|how|what|guide|advice|advice)\b",
}

# Rough Dubai budget bands (AED). Tunable; treat as suggestions, not promises.
# Case-insensitive; unit required when present (no trailing '?') so "1.2M" binds the M.
# Negative lookahead (?!\w) stops "3 months" from matching as 3 million. Bare numbers
# (no unit) fall through to the keyword fallback in _extract_budget.
_BUDGET_PATTERN = r"(?i)(?:aed|dh|dhs|dirham)?\s*(\d[\d.,]*)\s*(million|mn|bn|billion|thousand|m|k)(?!\w)"
_BUDGET_BANDS = [
    (0, 750_000, "0_750k"),
    (750_000, 1_500_000, "0.75M_1.5M"),
    (1_500_000, 3_000_000, "1.5M_3M"),
    (3_000_000, 10_000_000, "3M_10M"),
    (10_000_000, 10**12, "10M_plus"),
]

_TIMELINE_PATTERNS: dict[str, str] = {
    "urgent_0_1m": r"\b(asap|urgent|immediate|this week|right away)\b",
    "soon_0_3m": r"\b(\d?\s?months?|3 months|moving soon|q[1-4]|next quarter)\b",
    "exploratory": r"\b(exploring|just looking|curious|someday|future)\b",
}


class QualificationAgent(BaseAdapter):
    """Scores a captured lead and decides pipeline entry."""

    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        lead_id = payload.get("lead_id")
        msg = (payload.get("message") or "").lower().strip()
        handle = (payload.get("contact") or {}).get("handle", "")
        channel = (payload.get("contact") or {}).get("channel", "unknown")

        intent = self._classify_intent(msg)
        budget_band = self._extract_budget(msg)
        timeline = self._extract_timeline(msg)
        segment = self._segment(intent, handle, msg)

        # Scoring — transparent, additive. Cap at 100.
        score = 0
        score += 40 if budget_band != "unknown" else 0
        score += 30 if timeline != "unknown" else 0
        score += 30 if intent in ("buy", "sell", "rent") else 12
        score = min(score, 100)

        # Decision thresholds.
        if intent == "info":
            # Pure enquiry ("tell me about...") is a nurture lead, not spam.
            decision = "nurture_follow_up"
            status = "nurture"
        elif score >= 60 and intent in ("buy", "sell", "rent"):
            decision = "qualified_pipeline_entry"
            status = "qualified"
        elif score >= 35:
            decision = "nurture_follow_up"
            status = "nurture"
        else:
            decision = "drop_unfit_or_spam"
            status = "dropped"

        confidence = "high" if score >= 70 else "medium" if score >= 45 else "low"
        # Flag sparse-info cases honestly.
        if not budget_band or not timeline:
            confidence = "low" if confidence == "high" else confidence

        rationale = self._rationale(intent, budget_band, timeline, score)
        tags = [f"segment:{segment}", f"priority:{'high' if score >= 70 else 'med' if score >= 45 else 'low'}"]
        if intent != "info":
            tags.append(f"intent:{intent}")

        return {
            "lead_id": lead_id,
            "score": score,
            "segment": segment,
            "intent": intent,
            "timeline": timeline,
            "budget_band": budget_band,
            "decision": decision,
            "confidence": confidence,
            "rationale": rationale,
            "tags": tags,
            "status": status,
            "next": "route_to_geomatch" if status == "qualified" else "route_to_nurture",
        }

    # ── helpers ────────────────────────────────────────────────

    def _classify_intent(self, msg: str) -> str:
        for intent, pat in _INTENT_PATTERNS.items():
            if re.search(pat, msg):
                return intent
        return "info"

    def _extract_budget(self, msg: str) -> str:
        # Try a number-with-unit token first (e.g. "1.2M", "5 million", "2.5bn").
        m = re.search(_BUDGET_PATTERN, msg)
        if m:
            raw = m.group(1).replace(",", "")
            try:
                val = float(raw)
            except ValueError:
                val = 0.0
            unit = (m.group(2) or "").lower()
            if unit in ("m", "million"):
                val *= 1_000_000
            elif unit in ("k", "thousand"):
                val *= 1_000
            elif unit in ("b", "bn", "billion"):
                val *= 1_000_000_000
            # If a unit was present, use the scaled value; otherwise it's a
            # bare AED amount (e.g. "budget 1.2" with no unit).
            if val > 0:
                return self._band(val)
        # Fallback: any bare number near budget keywords (no unit).
        m2 = re.search(r"(?:budget|value|around|approx|worth|for)\s*(?:aed|dh|dhs|dirham)?\s*(\d[\d.,]*)", msg)
        if m2:
            try:
                val = float(m2.group(1).replace(",", ""))
            except ValueError:
                return "unknown"
            if val > 0:
                return self._band(val)
        return "unknown"

    def _band(self, val: float) -> str:
        for lo, hi, band in _BUDGET_BANDS:
            if lo <= val < hi:
                return band
        return "10M_plus" if val >= 10_000_000 else "unknown"

    def _extract_timeline(self, msg: str) -> str:
        for tl, pat in _TIMELINE_PATTERNS.items():
            if re.search(pat, msg):
                return tl
        return "unknown"

    def _segment(self, intent: str, handle: str, msg: str) -> str:
        if intent == "info":
            return "info_only"
        if re.search(r"\b(invest|roi|yield|portfolio|fund)\b", msg):
            return "investor"
        if re.search(r"\b(international|abroad|overseas|uk|us|eu)\b", msg):
            return "international_buyer"
        return "end_user_buyer"

    def _rationale(self, intent: str, budget: str, timeline: str, score: int) -> list[str]:
        out: list[str] = []
        if budget != "unknown":
            out.append(f"Stated budget band {budget} → +40")
        else:
            out.append("No budget stated → capped confidence")
        if timeline != "unknown":
            out.append(f"Timeline '{timeline}' → +30")
        else:
            out.append("No timeline → treating as exploratory")
        out.append(f"Intent '{intent}' → +{30 if intent in ('buy','sell','rent') else 12}")
        out.append(f"Composite score {score}/100")
        return out
