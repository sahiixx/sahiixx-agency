---
name: gcc-outbound-prospecting
version: 1.0.0
model: opus-4.8
runtime: claude-skill
---

# GCC Outbound Prospecting Skill

## Goal
Turn a target profile (company, role, LinkedIn URL, intent signal) into a personalized, multi-touch outbound sequence for Gulf-region prospects (UAE, KSA, Qatar, Bahrain, Kuwait, Oman).

## When to Use
- User provides a prospect URL, company name, or role + region.
- Intent is to generate cold email, LinkedIn message, or follow-up sequence.
- Language preference: English (business), with optional Arabic greeting localization.

## Input Schema
```json
{
  "prospect": {"name": "", "company": "", "role": "", "linkedin_url": "", "country": "AE|SA|QA|BH|KW|OM"},
  "our_company": {"name": "", "value_prop": "", "product": ""},
  "signal": {"type": "hiring|growth|news|event", "description": ""},
  "channels": ["email", "linkedin", "whatsapp"],
  "tone": "professional|casual|aggressive"
}
```

## Output
- `subject`: string
- `body`: string (plain text, no HTML)
- `follow_ups`: list of 3 short messages with delay hints (day 3, day 7, day 12)
- `localizations`: dict with Arabic greeting and Gulf business etiquette notes
- `confidence`: 0–1 score based on signal strength

## Prompt Template
```
You are a GCC outbound sales expert. Write a personalized {{channel}} outreach for {{prospect.name}} at {{prospect.company}} ({{prospect.role}}), based on this signal: {{signal.description}}.

Rules:
- Reference the signal explicitly in the first line.
- Keep the email under 120 words.
- Mention one specific Gulf business context (e.g., Saudization, NEOM, VAT, DIFC, Qatar National Vision 2030).
- End with a low-friction ask (reply, 15-min call, calendar link).
- Avoid jargon, buzzwords, and emojis.

Return JSON matching the Output schema above.
```

## Example
Input: `prospect={name:"Ahmed Al-Rashid", company:"NoorTech", role:"CTO", country:"AE"}, signal={type:"hiring", description:"NoorTech posted 5 senior AI engineer roles in Dubai in the last 14 days"}`
Output: personalized email + LinkedIn connection request + WhatsApp voice note script.

## Integration
- Exposed via `sahiixx_agency.adapters.skills.gcc_outbound` adapter.
- FastAPI endpoint: `POST /skills/gcc-outbound/prospect`.
- MCP tool: `gcc_outbound_prospect`.
