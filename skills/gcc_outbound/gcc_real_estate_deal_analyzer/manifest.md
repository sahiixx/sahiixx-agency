---
name: gcc-real-estate-deal-analyzer
version: 1.0.0
model: opus-4.8
runtime: claude-skill
---

# GCC Real-Estate Deal Analyzer Skill

## Goal
Evaluate off-plan / secondary real-estate deals in UAE/KSA/Qatar and produce a one-page investment memo with risk scoring, projected yield, and red flags.

## When to Use
- User pastes a property listing (URL or text).
- User asks "is this a good deal?", "analyze this property", or "compare these two deals".
- Region is Dubai, Abu Dhabi, Riyadh, Jeddah, Doha, or Lusail.

## Input Schema
```json
{
  "listing": {"title": "", "price_aed": 0, "price_sar": 0, "price_qar": 0, "location": "", "developer": "", "bedrooms": 0, "area_sqft": 0, "handover_year": 0, "url": ""},
  "purpose": "investment|end_use|flip",
  "financing": {"ltv": 0.0, "interest_rate": 0.0, "years": 0},
  "rental_comps": [{"location": "", "bedrooms": 0, "annual_rent": 0}]
}
```

## Output
- `summary`: 3-sentence verdict
- `metrics`: gross yield %, net yield %, price/sqft, price per bed, rental premium/discount
- `risk_score`: 0–100 (0 = low risk, 100 = high risk)
- `red_flags`: list
- `recommendation`: buy / negotiate / pass with reasons
- `comparison`: if multiple listings provided

## Prompt Template
```
You are a GCC real-estate investment analyst. Analyze the following property listing and produce a JSON object matching the Output schema.

Guidelines:
- Use Gulf-specific benchmarks: Dubai gross yield 6–8%, Riyadh 5–7%, Doha 6–8%.
- Flag risks: developer delay, off-plan payment plan, service charges, location oversupply, legal title issues (e.g., Oqood vs. title deed).
- Compare to provided rental comps.
- Be conservative on rental vacancy and service charges.
- Mention the specific market (e.g., Palm Jumeirah, Dubai Hills, Riyadh King Abdullah District, Lusail Marina).

Return JSON only.
```

## Integration
- Exposed via `sahiixx_agency.adapters.skills.gcc_outbound` adapter.
- FastAPI endpoint: `POST /skills/gcc-outbound/real-estate`.
- MCP tool: `gcc_real_estate_analyzer`.
