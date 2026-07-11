---
name: outbound-prospecting
description: Score and rank B2B prospects by buying/social signals, then draft personalized multichannel outreach (email + LinkedIn + follow-up) for the top ones. Use whenever the user asks to build a lead list, score or prioritize prospects, warm up outbound, or write outreach sequences for a GTM / sales motion.
---

# Outbound Prospecting (GCC / real-estate / tech ICP)

Turns a raw lead list into a ranked, signal-weighted prospect list with drafted touchpoints. Focuses on *warm* signals (funding, hiring, headcount growth, decision-maker presence) over cold scraping — same philosophy as a good SDR, not a bulk email blast.

## When to use
- "Score these leads", "rank these prospects", "who should I reach out to first"
- "Write outreach for [list]", "build a sequence for [ICP]"
- Prioritizing a CRM export by intent

## How to run

Score the list first — pass a JSON array of leads (file or stdin):

```bash
python .claude/skills/outbound-prospecting/scripts/score_leads.py < leads.json
# or
python .claude/skills/outbound-prospecting/scripts/score_leads.py --json '[{...}]'
```

### Lead schema
| Field | Meaning |
|---|---|
| `company` | Company name (required) |
| `domain` | Website (optional) |
| `locale` | City/country — affects channel + tone (e.g. "Dubai", "Riyadh", "Doha") |
| `decision_maker` | Name + title of the buyer (optional) |
| `signals` | Object of signal flags (see below) |
| `notes` | Free text |

Signal weights (each 0–1 unless noted): `funding_round` (×3), `hiring_growth` (×2), `new_leadership` (×2), `expansion` (new market/office, ×2), `engagement` (reply/event attendance, ×1.5), `icp_fit` (manual 0–1, ×2), `tech_stack_match` (×1).

The script prints a ranked JSON array with `score` (0–100), `tier` (S/A/B/C), and the dominant signals.

## Drafting outreach

For the top 3–5 S/A-tier prospects, write a per-prospect sequence:
1. **Email (cold)** — ≤120 words, one specific signal as the hook ("saw you raised Series B / opened a Dubai office / hired a new Head of Acquisitions"), one value prop tied to *their* signal, one soft CTA (a question or 15-min slot). No generic "I hope this finds you well."
2. **LinkedIn connect** — ≤300 chars, reference the same signal, no pitch.
3. **Follow-up #1 (day 4)** — ≤80 words, add one new data point or case-relevant angle.
4. **Break-up email (day 10)** — ≤60 words, permission-based close.

GCC tone notes:
- Dubai/Riyadh/Doha: lead with respect + context, avoid US-style aggressive "just checking in." Use "Salam" only if the lead's profile signals it — otherwise neutral English. Friday is a rest day in KSA; sequence around it.
- For real-estate principals / family offices: relationship-first, lead with credibility (track record, RERA registration) before any ask.
- For tech buyers: signal-led, proof-first.

## Output format
Return a short ranked table (company, tier, score, top signal), then the per-prospect sequences. Do not invent signals that aren't in the input — if a field is missing, say "unknown" rather than fabricating a funding round or hire.

## Limits
- Do not generate bulk cold-email spam templates. This skill is for *personalized* warm prospecting.
- Verify any "funding round" claim against a public source before publishing it in outreach — a wrong funding claim in a cold email is reputation damage.