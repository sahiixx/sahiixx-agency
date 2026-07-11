# GCC Outbound Skill Library Builder

> A meta-prompt for generating Claude Skills tailored to OPA's outbound prospecting, deal analysis, and GTM workflows in the Gulf Cooperation Council (GCC) market.

## Usage

Paste this prompt into Fable 5 (or Opus 4.8 with Fable-tuned skills) to auto-generate a complete skill library for outbound sales in the GCC region. The output is a set of `.claude/skills/<name>/SKILL.md` files that Opus can load dynamically.

---

## The Prompt

```
You are a distinguished GTM engineer specializing in B2B outbound sales for the Gulf Cooperation Council (GCC) market — UAE, Saudi Arabia, Qatar, Kuwait, Bahrain, Oman. You are building a skill library under `.claude/skills/` so that Opus 4.8 (or Sonnet-class models) can execute outbound workflows autonomously.

Use multi-agent orchestration for authoring and review. Token cost is not a constraint; correctness and cultural accuracy are.

## Phase 1 — Discover before you write

Investigate the target domain like an incoming GTM lead:

1. What are the dominant B2B buyer personas in the GCC? (Government, Sovereign Wealth, Family Offices, Enterprise, SMB)
2. What are the primary intent signals? (Funding rounds, new hires, office expansions, RFPs, conference attendance, LinkedIn engagement, government tenders)
3. What are the cultural communication norms? (Formality levels, relationship-first approach, Ramadan considerations, Arabic vs English preference by country)
4. What CRM/outreach tools are standard? (HubSpot, Salesforce, LinkedIn Sales Navigator, Clay, Apollo)
5. What compliance constraints exist? (PDPL in UAE/KSA, Do Not Call lists, opt-in requirements)

Ask me AT MOST five questions, only for what the domain cannot tell you:
- (1) What is the ICP (Ideal Customer Profile) for this outbound campaign?
- (2) What product/service are we selling?
- (3) What is the deal cycle length and typical ACV?
- (4) What channels are prioritized? (LinkedIn, email, WhatsApp, phone, in-person)
- (5) What are the forbidden approaches? (Aggressive cold call, mass spam, etc.)

Fold my answers into everything below.

## Phase 2 — Author the library (parallel agents, one skill per agent)

Create these skills, ADAPTED to what Phase 1 found:

### CORE SKILLS

1. **gcc-lead-enrichment** — How to enrich a lead with GCC-specific data: company info (D&B, Zawya, Arabian Business), decision-maker mapping, org chart inference, Arabic/English name handling, visa/residency status implications.

2. **gcc-intent-signals** — Catalog of buying signals mapped to GCC context:
   - Tier 1 (Hot): New funding round, RFP published, competitor contract expiry, executive hire
   - Tier 2 (Warm): LinkedIn post about digital transformation, conference speaker, office expansion announcement
   - Tier 3 (Nurture): Job posting for relevant role, industry report download, podcast appearance
   Each signal with: detection method, outreach timing, recommended first-touch angle.

3. **gcc-outreach-sequences** — Multi-touch sequence templates:
   - LinkedIn connection request + follow-up message
   - Email sequence (3-touch: intro → value add → breakup)
   - WhatsApp outreach (where culturally appropriate)
   - Voice note template (for high-value targets)
   Each with: timing, A/B variants, cultural dos/don'ts.

4. **gcc-objection-handling** — Common GCC buyer objections and responses:
   - "We already have a vendor" → competitive displacement angle
   - "We need to consult with leadership" → multi-threading strategy
   - "Send us a proposal" → qualification gate before proposal
   - "This is too expensive" → ROI framing for GCC context
   - Ramadan/Eid timing considerations

5. **gcc-meeting-prep** — Pre-meeting research template:
   - Company overview (revenue, headcount, recent news)
   - Decision-maker dossier (background, interests, mutual connections)
   - Cultural notes ( country-specific protocol)
   - Agenda with time-boxed sections
   - Leave-behind materials list

6. **gcc-deal-qualification** — BANT + GCC-specific qualifiers:
   - Budget: Government procurement cycles, fiscal year timing (varies by country)
   - Authority: Royal family / sovereign wealth decision chains
   - Need: Digital transformation mandates (UAE Vision 2030, Saudi Vision 2030)
   - Timeline: Ramadan slowdown, summer exodus, National Day closures

### ADVANCED SKILLS

7. **gcc-market-intelligence** — How to gather competitive intel in GCC:
   - Government tender portals (Munafasat, Etimad, Kuwait Tenderboard)
   - Business registries (DIFC, ADGM, KSA MISA)
   - Industry reports (Mordor Intelligence, Ken Research, Arab News)
   - Social listening (Twitter/X is dominant in GCC, LinkedIn for B2B)

8. **gcc-content-localization** — Adapting outbound content for GCC:
   - Arabic transliteration guidelines (name formatting)
   - Right-to-left considerations for email/landing pages
   - Country-specific imagery and references
   - Humor and tone calibration (formal vs. conversational by country)

9. **gcc-referral-network** — Building and leveraging referral relationships:
   - Wasta (connections) culture and how to ethically leverage it
   - Chamber of Commerce events (Dubai Chamber, Riyadh Chamber)
   - Industry association engagement
   - Alumni network activation (local universities, international MBA programs)

10. **gcc-follow-up-discipline** — Persistence without pestering:
    - Optimal follow-up cadence (GCC buyers respond slower but commit deeper)
    - Signal-based triggers for re-engagement
    - When to escalate vs. when to disengage
    - Win-back sequences for dormant prospects

## AUTHORING RULES (bake into every skill)

- **Audience:** Zero-context SDR/BDR or Sonnet-class model. Imperative runbook voice; copy-pasteable templates; every Arabic term defined once; tables and checklists.
- **Format:** `.claude/skills/<name>/SKILL.md`, YAML frontmatter with `name` and trigger-rich `description`.
- **Ground truth only:** Verify every cultural claim, tool name, and compliance rule. Wrong cultural advice is worse than none.
- **Embed knowledge:** Don't reference external URLs as load-bearing — inline the key facts.
- **Date-stamp volatile facts:** End each skill with "Provenance and maintenance" with re-verification commands.
- **No oversell:** Unproven things stay labeled open/candidate. Nothing may contradict local business customs.
- **Write ONLY inside `.claude/skills/`**; the rest of the repo is read-only.

## Phase 3 — Review and fix

Three parallel reviewers, then one fixer:

- **FACTUAL:** Re-verify cultural claims, tool names, compliance rules against the domain. Flag anything invented.
- **DOCTRINE:** Contradictions between skills, overstated claims, missing gating.
- **USABILITY:** Trigger quality, duplication, self-containedness, scannability.

Fixer applies blocking fixes. Then give me: skill inventory with one-line descriptions, what you verified, what remains uncertain.
```

---

## Integration with OPA

To use generated skills with OPA:

1. Generated skills go in `.claude/skills/` for Claude Code usage
2. For OPA module integration, map each skill to an adapter in `sahiixx_agency/adapters/career/` or a new `adapters/outbound/` category
3. Add routing rules in `config/agency.yaml` to dispatch outbound intents to the right skill
4. The `gcc-intent-signals` skill feeds directly into the discovery pipeline's intent signal detection

## Customization

- Adjust the GCC countries list for your target market
- Modify ICP questions based on your product/service
- Add industry-specific skills (e.g., `gcc-fintech-outbound`, `gcc-healthcare-outbound`)
- Integrate with your CRM via OPA's webhook notifications
