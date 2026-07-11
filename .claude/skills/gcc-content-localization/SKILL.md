---
name: gcc-content-localization
description: >
  Use when adapting outbound content for GCC audiences — Arabic transliteration,
  right-to-left considerations, country-specific imagery, tone calibration.
  Trigger on: "localize content", "Arabic version", "translate for GCC", "RTL", "cultural adaptation".
---

# GCC Content Localization

Adapting content for Gulf audiences — beyond simple translation.

## Arabic Transliteration Guidelines

**There is no single "correct" transliteration.** Be consistent within your content.

| English | Common Variants | Recommended |
|---------|----------------|-------------|
| Mohammed | Muhammad, Mohammad, Mohamed, Mohammed | Mohammed (most common in UAE) |
| Abdullah | Abdulah, Abdallah | Abdullah |
| Ahmed | Ahmad, Ahmed | Ahmed |
| Al / El | Al, El, Al- | Al (formal) |
| Bin / Ibn | Bin, Ibn, Bin- | Bin (UAE/Qatar), Ibn (Saudi formal) |

**Rules:**
- Always check how the person spells their own name (LinkedIn, email signature)
- Use their preferred spelling consistently
- Don't shorten Arabic names (e.g., don't call "Mohammed Al Maktoum" just "Mohammed")
- In formal communications, use full name + title

## Right-to-Left (RTL) Considerations

### Email
- Arabic emails render RTL in most email clients
-混合 content (Arabic + English) can cause alignment issues
- Test emails in Outlook (Arabic mode) before sending
- Keep subject lines short — RTL text wraps differently

### Landing Pages
- Use `dir="rtl"` on the HTML element for Arabic pages
- Mirror the layout — navigation on right, content flows right-to-left
- Images with text need to be recreated (can't just flip — text becomes unreadable)
- Numbers remain LTR even in RTL text (e.g., "2025" reads left-to-right)

### Documents
- PDFs with Arabic content need proper font embedding
- Use Arabic-friendly fonts: Arial, Calibri, Noto Sans Arabic, Cairo
- Tables with mixed content: numbers stay LTR, text goes RTL

## Country-Specific Imagery

| Country | Preferred Imagery | Avoid |
|---------|------------------|-------|
| UAE | Dubai skyline, modern architecture, diversity | Religious symbols, political imagery |
| Saudi Arabia | NEOM, Vision 2030 projects, heritage sites | Anything political, controversial images |
| Qatar | Education City, Lusail, World Cup legacy | Political commentary |
| Kuwait | Kuwait Tower, skyline, cultural heritage | Political imagery |
| Bahrain | Bahrain World Trade Center, Formula 1 | Sectarian imagery |
| Oman | Sultan Qaboos Mosque, natural landscapes | Political commentary |

**Rules:**
- Use diverse, professional imagery
- Show GCC-specific success stories, not US/Europe examples
- Avoid any imagery that could be seen as politically sensitive
- When in doubt, use abstract/modern design over photography

## Tone Calibration by Country

| Country | Formality | Communication Style |
|---------|-----------|---------------------|
| UAE | Moderate-High | Professional, relationship-oriented, bilingual |
| Saudi Arabia | High | Very formal, hierarchy matters, Arabic preferred |
| Qatar | Moderate-High | Professional, slightly more relaxed than Saudi |
| Kuwait | Moderate | Direct, relationship-driven, Arabic preferred |
| Bahrain | Moderate | Most Westernized, English OK |
| Oman | High | Formal, respectful, Arabic preferred |

**Universal rules:**
- Start formal, relax only after they do
- Never use humor that could be misunderstood cross-culturally
- Avoid idioms and slang (they don't translate well)
- Use "Inshallah" only if you're Muslim and it's genuine — don't fake it

## Email Template — Localized

```
Subject: [Arabic transliteration of company name] — [Topic]

[Arabic greeting if appropriate]:
- Formal: "السيد/السيدة [Name] المحترم/ة" (Dear Mr./Ms. [Name])
- Semi-formal: "معالي/سعادة [Name]" (Your Excellency/Excellency — for senior officials)
- English: "Dear Mr./Ms. [Last Name]"

Body:
[2-3 sentences maximum before getting to the point]
[The ask or value proposition]
[Clear next step with specific time]

Closing:
- Formal Arabic: "وتفضلوا بقبول فائق الاحترام والتقدير" (Please accept my highest regards)
- Formal English: "Best regards" or "Warm regards"
- Include: Full name, title, company, phone (with country code)
```

## Content Localization Checklist

Before publishing/sending GCC-targeted content:

- [ ] Arabic transliteration verified (name spelling)
- [ ] RTL layout tested (if Arabic version)
- [ ] Imagery is GCC-appropriate
- [ ] Tone matches country formality level
- [ ] No idioms or slang that don't translate
- [ ] Currency in AED/SAR/QAR (not USD unless international context)
- [ ] Date format: DD/MM/YYYY (not MM/DD/YYYY)
- [ ] Time format: 12-hour with AM/PM (GCC standard)
- [ ] Phone format: +971 XX XXX XXXX (UAE), +966 XX XXX XXXX (Saudi), etc.
- [ ] No politically sensitive content
- [ ] No religious references (unless genuine and relevant)
