---
name: gcc-market-signals
version: 1.0.0
model: opus-4.8
runtime: claude-skill
---

# GCC Market Signals Skill

## Goal
Continuously monitor and summarize market signals (hiring, funding, expansion, tenders, regulations) in the GCC that indicate outbound opportunity for a specific product or ICP.

## When to Use
- User wants a weekly signal digest.
- User asks "what's moving in UAE fintech?" or "Saudi AI hiring signals this week".
- Input is one or more `keywords` + `country` + `category`.

## Input Schema
```json
{
  "keywords": ["AI", "fintech", "proptech", "logistics"],
  "countries": ["AE", "SA", "QA"],
  "categories": ["hiring", "funding", "tender", "expansion", "regulation"],
  "time_window_days": 7,
  "max_signals": 20
}
```

## Output
- `signals`: list with `company`, `country`, `category`, `summary`, `source_hint`, `outbound_angle`, `urgency` (high/medium/low)
- `top_opportunities`: list of 3 highest-urgency signals with suggested action
- `digest`: paragraph summary for human SDR/AE

## Prompt Template
```
You are a GCC market intelligence analyst. Given the keywords and countries, generate a list of plausible but realistic market signals for the past {{time_window_days}} days. Each signal must include a company name, a concrete outbound angle, and a Gulf-specific context.

Do not fabricate real events; label them as "synthetic signal" if no live source is provided. In production, these signals are replaced by API feeds (LinkedIn, Preqin, Tenders, Google News).

Return JSON only.
```

## Integration
- Exposed via `sahiixx_agency.adapters.skills.gcc_outbound` adapter.
- FastAPI endpoint: `POST /skills/gcc-outbound/market-signals`.
- MCP tool: `gcc_market_signals`.
