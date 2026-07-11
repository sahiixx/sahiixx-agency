---
name: gcc-intent-signals
description: >
  Use when identifying buying intent signals for GCC prospects — detect hot/warm/nurture
  signals from news, job postings, social media, or company announcements.
  Trigger on: "intent signals", "buying signals", "is this company ready to buy", "should I reach out".
---

# GCC Intent Signals

Detect and categorize buying signals specific to the GCC market.

## Signal Tiers

### Tier 1 — HOT (reach out within 24-48 hours)

| Signal | Detection Method | Outreach Angle |
|--------|-----------------|----------------|
| Funding round announced | Crunchbase, Zawya, press release | "Congrats on the round — how are you planning to scale the tech team?" |
| RFP/tender published | Government portals (Munafasat, Etimad), company site | Reference the RFP directly; demonstrate relevant capabilities |
| Competitor contract expiry | LinkedIn job changes, news, procurement data | Competitive displacement — highlight differentiation |
| Executive hire (CTO/CIO/CISO) | LinkedIn, press release | Welcome new exec; offer to help with their priorities |
| Merger/acquisition announced | Zawya, Arabian Business, Bloomberg | Integration creates vendor consolidation opportunity |

### Tier 2 — WARM (reach out within 1 week)

| Signal | Detection Method | Outreach Angle |
|--------|-----------------|----------------|
| Digital transformation post | LinkedIn, company blog | Share relevant case study or insight |
| Office expansion announced | News, LinkedIn, government announcements | "Congrats on the expansion — need help scaling ops?" |
| Conference speaker appearance | Event websites, LinkedIn | Reference their talk; share related content |
| Job posting for relevant role | LinkedIn, company careers page | "Hiring for X? We can supplement while you build the team" |
| New product launch | News, social media | Compliment the launch; identify integration opportunities |

### Tier 3 — NURTURE (monitor, engage quarterly)

| Signal | Detection Method | Outreach Angle |
|--------|-----------------|----------------|
| Industry report published | Company blog, social | Reference the report; share your data/perspective |
| Podcast appearance | Podcast platforms, LinkedIn | "Great episode — here's a related insight" |
| Social engagement with your content | LinkedIn notifications | Thank them; deepen the relationship |
| Job posting (non-relevant role) | LinkedIn | Company is investing — keep them on radar |
| Website redesign | Visual check, Wayback Machine | Modernization signal — they may be updating tech stack |

## GCC-Specific Signals

| Signal | What It Means | Action |
|--------|--------------|--------|
| Government tender issued | Budget allocated, procurement active | Register on portal; prepare compliant proposal |
| Vision 2030 project announcement | National priority = guaranteed funding | Align your solution with strategy goals |
| Free zone entity formation | New company = new vendor relationships | Early mover advantage — reach out before competitors |
| Royal family / sovereign wealth investment | Deep pockets, long-term commitment | Executive-level outreach required |
| Ramadan/Eid greetings from company | Relationship-oriented culture | Send appropriate greetings; don't sell during holy periods |

## Signal Strength Scoring

```
Score = (Signal Count × Tier Weight) × Freshness Multiplier

Tier Weights:  HOT = 3.0, WARM = 2.0, NURTURE = 1.0
Freshness:     This week = 1.0, This month = 0.7, Older = 0.4

Example:
  2 HOT signals (this week) + 1 WARM signal = (2×3 + 1×2) × 1.0 = 8.0
  → High priority — reach out immediately
```

## When NOT to Reach Out

- **During Ramadan** (unless they initiate) — relationship building only
- **During Eid al-Fitr / Eid al-Adha** (first 3-5 days) — send greetings only
- **Summer exodus** (July-August, especially UAE) — many decision-makers are traveling
- **National Day weeks** (varies by country) — government entities are closed
- **After a negative news event** (layoffs, scandal) — wait 2 weeks minimum

## Integration with OPA

The `detect_signals()` function in `sahiixx_agency/discovery/intent_signals.py` automates Tier 1-3 pattern matching. Feed text from news, job postings, or social media into it for instant signal detection.
