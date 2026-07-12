"""GCC Outbound Skill Library adapter for OPA.

Exposes four Opus-4.8 skills as agency tools:
- gcc_outbound_prospecting
- gcc_real_estate_deal_analyzer
- gcc_lead_scoring
- gcc_market_signals

The adapter renders prompt manifests against Jinja2 templates and returns
synthetic but structured results. In production, the prompts can be sent to
Opus 4.8 or any configured LLM provider via the OPA LLM manager.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

from jinja2 import BaseLoader, Environment

from sahiixx_agency.adapters.base import BaseAdapter

SKILL_DIR = Path(__file__).parent.parent.parent.parent / "skills" / "gcc_outbound"


class GccOutboundSkillAdapter(BaseAdapter):
    """Adapter for the GCC Outbound Skill Library."""

    def __init__(self, module: Any | None = None, llm_manager: Any | None = None) -> None:
        super().__init__()
        self.module = module
        self.llm_manager = llm_manager
        self._jinja = Environment(loader=BaseLoader(), autoescape=False)

    @property
    def module_id(self) -> str:
        return "gcc_outbound_skill_library"

    def _render_manifest(self, skill_name: str, context: dict[str, Any]) -> str:
        manifest_path = SKILL_DIR / skill_name / "manifest.md"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Skill manifest not found: {manifest_path}")
        template = self._jinja.from_string(manifest_path.read_text(encoding="utf-8"))
        return template.render(**context)

    def list_skills(self) -> list[str]:
        """Return the names of all available GCC outbound skills."""
        if not SKILL_DIR.exists():
            return []
        return [p.name for p in SKILL_DIR.iterdir() if p.is_dir() and (p / "manifest.md").exists()]

    def load_manifest(self, skill_name: str, context: dict[str, Any] | None = None) -> str:
        """Render a skill manifest with the supplied context."""
        return self._render_manifest(skill_name, context or {})

    def _extract_prompt(self, manifest: str) -> str:
        # Naive markdown extraction: find the ``` prompt block.
        start = manifest.find("```")
        end = manifest.find("```", start + 3)
        if start == -1 or end == -1:
            return manifest
        return manifest[start + 3 : end].strip()

    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        skill = payload.get("skill", "gcc_outbound_prospecting")
        context = payload.get("context", {})

        if skill == "gcc_outbound_prospecting":
            return self._prospect(context)
        if skill == "gcc_real_estate_deal_analyzer":
            return self._analyze_real_estate(context)
        if skill == "gcc_lead_scoring":
            return self._score_leads(context)
        if skill == "gcc_market_signals":
            return self._market_signals(context)

        raise ValueError(f"Unknown GCC outbound skill: {skill}")

    def _prospect(self, context: dict[str, Any]) -> dict[str, Any]:
        prospect = context.get("prospect", {})
        signal = context.get("signal", {})
        our_company = context.get("our_company", {})

        name = prospect.get("name", "there")
        company = prospect.get("company", "your company")
        role = prospect.get("role", "leader")
        country = prospect.get("country", "AE")
        signal_desc = signal.get("description", "recent activity")
        value_prop = our_company.get("value_prop", "our solution")

        arabic_greeting = {"AE": "As-salamu alaykum", "SA": "As-salamu alaykum", "QA": "As-salamu alaykum", "BH": "As-salamu alaykum", "KW": "As-salamu alaykum", "OM": "As-salamu alaykum"}.get(country, "Hello")
        market_note = {
            "AE": "the Dubai / DIFC ecosystem",
            "SA": "Saudi Vision 2030 and Saudization",
            "QA": "Qatar National Vision 2030 and Lusail",
            "BH": "Bahrain fintech Bay",
            "KW": "Kuwait Vision 2035",
            "OM": "Oman Vision 2040",
        }.get(country, "the GCC market")

        subject = f"{company} + {our_company.get('name', 'us')} — {signal_desc[:40]}"
        body = (
            f"{arabic_greeting} {name},\n\n"
            f"I noticed {signal_desc} at {company}. Given your role as {role}, "
            f"this likely means {company} is expanding its capability in {market_note}.\n\n"
            f"{value_prop}. Would it make sense to explore how we can support this initiative?\n\n"
            f"Best,\n{our_company.get('name', 'Our team')}"
        )

        follow_ups = [
            {"delay_days": 3, "message": f"Quick follow-up, {name} — wanted to share a case study from a similar {role} in {country}."},
            {"delay_days": 7, "message": f"Hi {name}, checking if now is a better time to discuss {value_prop.lower()} for {company}."},
            {"delay_days": 12, "message": f"Last note from me, {name} — happy to send a one-page overview tailored to {company}."},
        ]

        return {
            "skill": "gcc_outbound_prospecting",
            "subject": subject,
            "body": body,
            "follow_ups": follow_ups,
            "localizations": {
                "arabic_greeting": arabic_greeting,
                "business_etiquette": "Use formal titles, avoid hard sells, respect Friday/Saturday weekend boundaries.",
            },
            "confidence": round(0.75 + random.random() * 0.2, 2),
        }

    def _analyze_real_estate(self, context: dict[str, Any]) -> dict[str, Any]:
        listing = context.get("listing", {})
        purpose = context.get("purpose", "investment")
        price = listing.get("price_aed", 0) or listing.get("price_sar", 0) or listing.get("price_qar", 0)
        area = listing.get("area_sqft", 1) or 1
        location = listing.get("location", "Unknown")
        country = listing.get("country", "AE")

        yield_benchmark = {"AE": 7.0, "SA": 6.0, "QA": 7.0, "BH": 7.5, "KW": 6.5, "OM": 6.5}.get(country, 6.5)
        gross_yield = round((price * 0.07) / max(price, 1) * 100, 2) if price else yield_benchmark
        risk_score = random.randint(30, 65)

        return {
            "skill": "gcc_real_estate_deal_analyzer",
            "summary": f"{listing.get('title', 'Property')} in {location} shows a {purpose} profile with a gross yield near {gross_yield}%.",
            "metrics": {
                "gross_yield_pct": gross_yield,
                "net_yield_pct": round(gross_yield - 1.5, 2),
                "price_per_sqft": round(price / area, 2),
                "price_per_bed": round(price / max(listing.get("bedrooms", 1), 1), 2),
            },
            "risk_score": risk_score,
            "red_flags": ["Off-plan payment plan", "Service charges not disclosed"] if listing.get("handover_year", 2030) > 2027 else ["Service charges not disclosed"],
            "recommendation": "negotiate" if risk_score > 50 else "buy",
            "country": country,
        }

    def _score_leads(self, context: dict[str, Any]) -> dict[str, Any]:
        leads = context.get("leads", [])
        icp = context.get("icp", {})
        target_countries = set(icp.get("target_countries", []))
        target_roles = [r.lower() for r in icp.get("target_roles", [])]
        max_results = context.get("max_results", 10)

        scored = []
        for lead in leads:
            fit = 0
            if not target_countries or lead.get("country", "") in target_countries:
                fit += 20
            if any(r in lead.get("role", "").lower() for r in target_roles):
                fit += 20
            intent = min(35, 10 + len(lead.get("signal", "")) // 5)
            reach = 25 if lead.get("linkedin_url") or lead.get("email") else 10
            score = min(100, fit + intent + reach + random.randint(0, 10))
            scored.append({
                **lead,
                "score": score,
                "fit_score": fit,
                "intent_score": intent,
                "reachability_score": reach,
                "reason": f"Strong ICP + signal match in {lead.get('country', 'region')}." if score >= 80 else "Moderate fit; nurture or disqualify.",
                "suggested_action": "email now" if score >= 80 else "linkedin connect" if score >= 60 else "nurture",
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return {"skill": "gcc_lead_scoring", "scored_leads": scored[:max_results]}

    def _market_signals(self, context: dict[str, Any]) -> dict[str, Any]:
        keywords = context.get("keywords", ["AI"])
        countries = context.get("countries", ["AE"])
        categories = context.get("categories", ["hiring"])
        max_signals = context.get("max_signals", 10)

        signals = []
        for i in range(max_signals):
            keyword = keywords[i % len(keywords)]
            country = countries[i % len(countries)]
            category = categories[i % len(categories)]
            signals.append({
                "company": f"{keyword.capitalize()} Gulf Solutions {i + 1}",
                "country": country,
                "category": category,
                "summary": f"{keyword} activity detected in {country}.",
                "source_hint": "synthetic signal",
                "outbound_angle": f"Position {keyword} consulting/services for {country}-based expansion.",
                "urgency": "high" if category == "funding" else "medium",
            })

        return {
            "skill": "gcc_market_signals",
            "signals": signals,
            "top_opportunities": signals[:3],
            "digest": f"Detected {len(signals)} synthetic signals across {', '.join(countries)} for {', '.join(keywords)}.",
        }
