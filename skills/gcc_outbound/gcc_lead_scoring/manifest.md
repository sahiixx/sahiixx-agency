---
name: gcc-lead-scoring
version: 1.0.0
model: opus-4.8
runtime: claude-skill
---

# GCC Lead Scoring Skill

## Goal
Score inbound or outbound leads in the GCC based on fit, intent, and reachability, then prioritize the top N leads for a human AE or SDR.

## When to Use
- User provides a CSV, JSON list, or pasted list of leads.
- Intent is to prioritize outreach, assign to AE, or detect ICP matches.

## Input Schema
```json
{
  "leads": [
    {"name": "", "company": "", "role": "", "country": "AE|SA|QA|BH|KW|OM", "source": "", "signal": ""}
  ],
  "icp": {"target_roles": [], "target_countries": [], "target_company_sizes": [], "required_signals": []},
  "max_results": 10
}
```

## Output
- `scored_leads`: list sorted by score descending
- Each lead gets: `score` (0–100), `fit_score`, `intent_score`, `reachability_score`, `reason`, `suggested_action`

## Scoring Rules
- Fit (40): role match, company size, country match.
- Intent (35): explicit signal (hiring, funding, expansion, tender, event).
- Reachability (25): has email, LinkedIn, phone, or is in an existing sequence.
- Bonus: responds to previous outreach, attended a Gulf event, or is a referral.

## Prompt Template
```
You are a GCC B2B lead-scoring engine. Score each lead in the input list against the provided ICP and return a ranked JSON list.

Rules:
- Be strict: only high scores for strong ICP + intent + reachability alignment.
- Include a one-sentence reason for each score.
- Suggest the next action: "email now", "linkedin connect", "call today", "nurture", or "disqualify".
- For GCC context, consider Saudization, Emiratisation, government tenders, and free-zone presence as positive signals.

Return JSON only.
```

## Integration
- Exposed via `sahiixx_agency.adapters.skills.gcc_outbound` adapter.
- FastAPI endpoint: `POST /skills/gcc-outbound/lead-score`.
- MCP tool: `gcc_lead_score`.
