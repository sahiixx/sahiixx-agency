---
name: realestate-deal-analyzer
description: Compute Dubai/GCC residential investment metrics (net yield, cash-on-cash, DSCR, payback, breakeven occupancy) from property + financing inputs and produce a risk-weighted investor brief. Use whenever the user asks to analyze, score, or compare a real-estate deal, evaluate rental yield vs. financing, or build an investor one-pager for a property.
---

# Real-Estate Deal Analyzer (Dubai / GCC)

Analyzes a single property as an investment: runs the numbers, then drafts a risk-weighted investor brief. Tuned for Dubai/GCC conventions (DLD 4% transfer fee, 2% agent, service charges, typical mortgage terms).

## When to use
- "Analyze this deal", "what's the yield on...", "should I buy unit X for rental"
- Comparing two properties on cash-flow / return
- Producing an investor one-pager or brief

## How to run

Always run the script for the hard numbers — do not hand-compute. Pass inputs as a JSON object (file path or stdin):

```bash
python .claude/skills/realestate-deal-analyzer/scripts/analyze_deal.py < inputs.json
# or
python .claude/skills/realestate-deal-analyzer/scripts/analyze_deal.py --json '{"price":2500000,...}'
```

### Required inputs (AED unless noted)
| Field | Meaning |
|---|---|
| `price` | Property purchase price (AED) |
| `annual_rent` | Gross expected annual rent (AED) |
| `service_charges` | Annual service/maintenance charges (AED) |
| `vacancy_pct` | Expected vacancy + non-payment buffer (%, default 5) |
| `downpayment_pct` | Down payment (%, default 25 — Dubai investor mortgage floor) |
| `rate_pct` | Mortgage annual interest (%, default 4.5) |
| `years` | Mortgage term (years, default 25) |
| `agent_fee_pct`, `dld_fee_pct`, `other_one_time` | One-time acquisition costs (defaults: 2, 4, 0) |

The script prints a JSON metrics object: `gross_yield`, `net_yield`, `monthly_cashflow`, `annual_cashflow`, `cash_on_cash`, `dscr`, `payback_years`, `breakeven_occupancy_pct`, `lvr`.

## Producing the brief

After the script prints metrics, write a short investor brief with:
1. **Headline** — net yield, cash-on-cash, and a one-line verdict (acquire / pass / margin).
2. **Cash flow** — monthly net, and whether it covers the mortgage (DSCR ≥ 1.25 = healthy).
3. **Sensitivity** — re-run the script with rent ±10% and vacancy +5pp; report how the verdict flips. This is the most important section — deals look good at base case and break on rent dips.
4. **Risks** — RERA/DLD compliance notes, off-plan vs. ready, service-charge escalation, exit liquidity.
5. **Verdict** — Go / No-go / Conditional, with the single condition that would flip it.

Keep the brief under ~250 words. Use AED. Do not give legal/RERA advice beyond flagging — ask the user for a RERA-licensed broker when client-facing.

## RERA/DLD notes (flag, don't advise)
- Dubai off-plan: escrow accounts, RERA developer registration required. Ready: DLD 4% + mortgage registration (0.25% + AED 290 + trustee fees ~AED 4k+).
- Service charges are per sqft, set by RERA-approved JSP/Oqood — verify the latest NOC, not the brochure figure.
- When producing client-facing copy, confirm RERA rules with a licensed broker before publishing.