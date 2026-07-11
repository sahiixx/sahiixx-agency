#!/usr/bin/env python3
"""Dubai/GCC real-estate deal analyzer — computes investment metrics from a JSON input.

Stdlib-only. Reads JSON from --json '...' or stdin. Prints a JSON metrics object.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from typing import Any


def _monthly_payment(principal: float, annual_rate_pct: float, years: int) -> float:
    """Amortized monthly mortgage payment."""
    r = annual_rate_pct / 100 / 12
    n = years * 12
    if r == 0:
        return principal / n
    return principal * r * (1 + r) ** n / ((1 + r) ** n - 1)


def analyze(d: dict[str, Any]) -> dict[str, float | int | str]:
    price = float(d["price"])
    annual_rent = float(d["annual_rent"])
    service_charges = float(d.get("service_charges", 0))
    vacancy_pct = float(d.get("vacancy_pct", 5))
    downpayment_pct = float(d.get("downpayment_pct", 25))
    rate_pct = float(d.get("rate_pct", 4.5))
    years = int(d.get("years", 25))
    agent_fee_pct = float(d.get("agent_fee_pct", 2))
    dld_fee_pct = float(d.get("dld_fee_pct", 4))
    other_one_time = float(d.get("other_one_time", 0))

    downpayment = price * downpayment_pct / 100
    loan = price - downpayment
    one_time = price * (agent_fee_pct + dld_fee_pct) / 100 + other_one_time
    cash_in = downpayment + one_time  # total equity deployed at closing

    effective_rent = annual_rent * (1 - vacancy_pct / 100)
    noi = effective_rent - service_charges  # net operating income (pre-financing)
    gross_yield = annual_rent / price * 100 if price else 0
    net_yield = noi / price * 100 if price else 0

    monthly_payment = _monthly_payment(loan, rate_pct, years)
    monthly_cashflow = (noi / 12) - monthly_payment
    annual_cashflow = monthly_cashflow * 12

    cash_on_cash = annual_cashflow / cash_in * 100 if cash_in else 0
    dscr = (noi / 12) / monthly_payment if monthly_payment else float("inf")
    payback_years = cash_in / annual_cashflow if annual_cashflow > 0 else float("inf")
    breakeven_occupancy = (service_charges + monthly_payment * 12) / annual_rent * 100 if annual_rent else 100
    lvr = loan / price * 100 if price else 0

    return {
        "gross_yield_pct": round(gross_yield, 2),
        "net_yield_pct": round(net_yield, 2),
        "monthly_cashflow": round(monthly_cashflow, 0),
        "annual_cashflow": round(annual_cashflow, 0),
        "cash_on_cash_pct": round(cash_on_cash, 2),
        "dscr": round(dscr, 2) if math.isfinite(dscr) else "inf",
        "payback_years": round(payback_years, 1) if math.isfinite(payback_years) else "inf",
        "breakeven_occupancy_pct": round(breakeven_occupancy, 1),
        "lvr_pct": round(lvr, 1),
        "monthly_payment": round(monthly_payment, 0),
        "equity_deployed": round(cash_in, 0),
        "loan_amount": round(loan, 0),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Dubai/GCC real-estate deal analyzer")
    ap.add_argument("--json", help="JSON input string")
    args = ap.parse_args()

    if args.json:
        data = json.loads(args.json)
    else:
        raw = sys.stdin.read().strip()
        if not raw:
            print("Usage: analyze_deal.py --json '{...}'  or pipe JSON via stdin", file=sys.stderr)
            return 2
        data = json.loads(raw)

    missing = [k for k in ("price", "annual_rent") if k not in data]
    if missing:
        print(f"Missing required fields: {missing}", file=sys.stderr)
        return 2

    print(json.dumps(analyze(data), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())