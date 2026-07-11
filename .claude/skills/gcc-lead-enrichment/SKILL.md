---
name: gcc-lead-enrichment
description: >
  Use when enriching a B2B lead with GCC-specific data — company info, decision-maker
  mapping, org chart inference, Arabic/English name handling, or visa/residency context.
  Trigger on: "enrich lead", "research company", "find decision maker", "who is the buyer".
---

# GCC Lead Enrichment

Enrich leads with Gulf-specific data that generic enrichment tools miss.

## Data Sources (priority order)

| Source | What it covers | Access |
|--------|---------------|--------|
| Zawya (zawya.com) | Company financials, ownership, executives (UAE/Qatar/Kuwait) | Free tier available |
| Arabian Business | News, rankings, executive mentions | Public |
| D&B Hoovers | Global company data with GCC coverage | Paid |
| DIFC Register | Dubai International Financial Centre entities | Public |
| ADGM Register | Abu Dhabi Global Market entities | Public |
| KSA MISA | Saudi Ministry of Investment — foreign company registrations | Public |
| OpenSaq (Saudi) | Government procurement data | Public |
| LinkedIn Sales Navigator | Decision-maker identification, activity | Paid |

## Enrichment Checklist

For each lead, gather:

- [ ] **Company basics:** Legal name, trading name (may differ), parent company, subsidiaries
- [ ] **Ownership structure:** Family-owned? Government-linked? Sovereign wealth stake?
- [ ] **Decision-maker:** Name, title, LinkedIn profile, recent activity
- [ ] **Budget signals:** Recent funding, contract wins, expansion news
- [ ] **Cultural context:** Country HQ, primary language, formality level
- [ ] **Tech stack:** What tools they use (check job postings, LinkedIn, BuiltWith)

## Arabic/English Name Handling

- **Transliteration varies:** Mohammed = Muhammad = Mohammad = Mohamed. Search all variants.
- **Name order:** Arabic names often have patronymic chains (bin/ibn/bin). The "last" name may not be the family name.
- **Company names:** May appear in Arabic script, English, or both. Check both on LinkedIn.
- **Honorifics:** Use "Mr." / "Ms." in first contact unless you confirm they prefer first-name basis.

## Decision-Maker Mapping

```
Typical GCC Enterprise Decision Chain:
┌─────────────────────────────────────────┐
│  Board / Owner Family                   │ ← Final approval (large deals)
│  └── CEO / Managing Director            │ ← Strategic sign-off
│      └── CTO / CIO / VP Engineering     │ ← Technical evaluation
│          └── IT Manager / Procurement    │ ← Vendor shortlist
│              └── End Users               │ ← Influence only
└─────────────────────────────────────────┘
```

**Rules:**
- In family-owned businesses, the owner may bypass the entire chain. Identify family members.
- In government entities, procurement follows strict process — don't skip steps.
- In free zone companies (DIFC/ADGM), decision chains are flatter and more Western.

## Visa/Residency Implications

- **UAE Golden Visa holders** have more stability — longer deal cycles are acceptable.
- **Company sponsors (kafala)** — the sponsor controls residency. Key contact may change if they leave.
- **Free zone vs. mainland:** Free zone companies have different procurement rules.

## Output Format

After enrichment, produce:

```
## Lead Brief: [Company Name]

**Company:** [legal name] | [trading name if different]
**HQ:** [City, Country] | **Size:** [employees] | **Revenue:** [if known]
**Ownership:** [family/government/public/mixed]
**Parent:** [if applicable]

**Decision Maker:** [Name] | [Title] | [LinkedIn URL]
**Recent Activity:** [last 3 relevant posts/activities]

**Budget Signals:**
- [signal 1]
- [signal 2]

**Cultural Notes:**
- [formality level]
- [language preference]
- [any protocol notes]

**Recommended Approach:** [1-2 sentences on how to engage]
```
