#!/usr/bin/env python3
"""Outbound prospecting lead scorer — ranks leads by buying/social signals.

Stdlib-only. Reads a JSON array of leads from --json '...' or stdin.
Prints a ranked JSON array with score (0-100), tier (S/A/B/C), and dominant signals.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from typing import Any

# signal -> weight
WEIGHTS: dict[str, float] = {
    "funding_round": 3.0,
    "hiring_growth": 2.0,
    "new_leadership": 2.0,
    "expansion": 2.0,
    "engagement": 1.5,
    "icp_fit": 2.0,
    "tech_stack_match": 1.0,
}


def _tier(score: float) -> str:
    if score >= 75:
        return "S"
    if score >= 55:
        return "A"
    if score >= 35:
        return "B"
    return "C"


def score_lead(lead: dict[str, Any]) -> dict[str, Any]:
    signals: dict[str, Any] = lead.get("signals") or {}
    weighted_total = 0.0
    contributing: list[str] = []

    for sig, weight in WEIGHTS.items():
        val = signals.get(sig, 0)
        if isinstance(val, bool):
            val = 1.0 if val else 0.0
        try:
            val = float(val)
        except (TypeError, ValueError):
            val = 0.0
        val = max(0.0, min(1.0, val))  # clamp to [0,1]
        contribution = val * weight
        weighted_total += contribution
        if val >= 0.5:
            contributing.append(sig)

    # Saturating curve so a few strong signals reach A/S tier (a funded +
    # expanding + ICP-fit lead is genuinely hot, not "B-tier"). Score = 100*(1-e^(-w/4.5)).
    # Single funding signal ~ B; funding+hiring ~ A; funded+expanding+ICP ~ S; cold ~ C.
    score = round(100 * (1 - math.exp(-weighted_total / 4.5)), 1) if weighted_total > 0 else 0.0

    result = dict(lead)
    result["score"] = score
    result["tier"] = _tier(score)
    result["dominant_signals"] = contributing
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Outbound prospecting lead scorer")
    ap.add_argument("--json", help="JSON array of leads")
    args = ap.parse_args()

    if args.json:
        leads = json.loads(args.json)
    else:
        raw = sys.stdin.read().strip()
        if not raw:
            print("Usage: score_leads.py --json '[...]'  or pipe a JSON array via stdin", file=sys.stderr)
            return 2
        leads = json.loads(raw)

    if not isinstance(leads, list):
        print("Input must be a JSON array of lead objects", file=sys.stderr)
        return 2

    scored = [score_lead(l) for l in leads if isinstance(l, dict)]
    scored.sort(key=lambda x: x["score"], reverse=True)

    print(json.dumps(scored, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())