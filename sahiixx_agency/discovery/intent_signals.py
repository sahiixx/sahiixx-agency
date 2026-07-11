"""Gojiberry-style intent signal detection for the discovery pipeline.

Detects buying signals from public data sources to identify high-intent
prospects for outbound sales workflows. Inspired by Gojiberry AI's approach
of monitoring 15+ buying and social signals.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

import httpx
from pydantic import BaseModel, Field


class SignalTier(str, Enum):
    """Intent signal temperature tiers."""

    HOT = "hot"  # Tier 1: Active buying signals
    WARM = "warm"  # Tier 2: Interest signals
    NURTURE = "nurture"  # Tier 3: Awareness signals


class IntentSignal(BaseModel):
    """A detected buying intent signal."""

    signal_type: str
    tier: SignalTier
    source: str
    confidence: float = Field(ge=0.0, le=1.0)
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw_data: dict[str, Any] = Field(default_factory=dict)
    recommended_action: str = ""
    outreach_angle: str = ""


class IntentSignalResult(BaseModel):
    """Aggregated intent signals for a company/entity."""

    entity_name: str
    entity_url: str = ""
    signals: list[IntentSignal] = Field(default_factory=list)
    overall_tier: SignalTier = SignalTier.NURTURE
    score: float = 0.0
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ─── Signal Detection Patterns ──────────────────────────────────

# Tier 1 (Hot) signals — direct buying intent
# NOTE: All patterns are lowercase because matching is done on text.lower()
HOT_SIGNAL_PATTERNS: dict[str, list[str]] = {
    "funding_round": [
        r"raised?\s+(?:a\s+)?(?:series\s+[a-z]|\$[\d.]+[mbk])",
        r"secures?\s+(?:a\s+)?(?:funding|investment|round)",
        r"closed?\s+(?:a\s+)?(?:series\s+[a-z]|funding|round)",
        r"valuation\s+of\s+\$[\d.]+",
    ],
    "rfp_published": [
        r"(?:request\s+for\s+(?:proposal|tender|quote)|rfp|rfq|rfi)",
        r"(?:invit(?:ing|ed)\s+(?:tenders?|proposals?|bids?))",
        r"(?:tender\s+(?:notice|announcement|call|for))",
    ],
    "competitor_contract_expiry": [
        r"(?:contract|agreement)\s+(?:expir|renew)",
        r"(?:switch(?:ing|ed)?|migrat(?:ing|ed)?)\s+(?:from|away\s+from)\s+",
        r"(?:looking\s+for\s+(?:alternatives?|replacements?|new\s+vendor))",
    ],
    "executive_hire": [
        r"(?:appoint(?:ed|s)?|joins?|hired?\s+as)\s+(?:new\s+)?(?:cto|cio|ciso|vp\s+(?:engineering|it|sales)|head\s+of\s+(?:engineering|it|security))",
        r"(?:new\s+)?(?:cto|cio|ciso)\s+(?:appointed|hired|joins?)",
    ],
}

# Tier 2 (Warm) signals — interest indicators
WARM_SIGNAL_PATTERNS: dict[str, list[str]] = {
    "digital_transformation_post": [
        r"(?:digital\s+transformation|moderniz(?:ing|ation)|cloud\s+migration|ai\s+adoption)",
        r"(?:looking\s+to\s+(?:automate|streamline|optimize|transform))",
        r"(?:investing\s+in\s+(?:technology|infrastructure|platform))",
    ],
    "conference_speaker": [
        r"(?:speaker|presenter|panelist)\s+(?:at|for|during)\s+",
        r"(?:keynote|talk|session|workshop)\s+(?:at|for)\s+",
    ],
    "office_expansion": [
        r"(?:opening|opens?|expanded?|expanding)\s+(?:new\s+)?(?:office|headquarters|hub|center)",
        r"(?:relocat(?:ing|ed)|mov(?:ing|ed)\s+to)\s+(?:larger|new|bigger)\s+(?:office|space)",
        r"(?:hiring\s+\d+|job\s+(?:opening|posting|vacancy))\s+(?:in|for)",
    ],
    "job_posting_relevant": [
        r"(?:hiring|looking\s+for|seeking)\s+(?:a\s+)?(?:software\s+engineer|developer|devops|security\s+engineer|data\s+engineer|ml\s+engineer|sre|platform\s+engineer)",
    ],
}

# Tier 3 (Nurture) signals — awareness indicators
NURTURE_SIGNAL_PATTERNS: dict[str, list[str]] = {
    "industry_report": [
        r"(?:published|released|shared|posted)\s+(?:a\s+)?(?:report|whitepaper|ebook|guide|benchmark)",
        r"(?:download(?:ed|ing)|access(?:ed|ing))\s+(?:our|the|a)\s+(?:report|whitepaper|ebook)",
    ],
    "podcast_appearance": [
        r"(?:guest|appeared|interviewed)\s+(?:on|in)\s+",
        r"(?:episode|podcast|interview)\s+(?:with|featuring|on|about|show)\s+",
        r"(?:podcast|show)\s+(?:appearance|interview|episode|featuring)",
    ],
    "social_engagement": [
        r"(?:liked|commented|shared|reposted)\s+(?:a\s+)?(?:post\s+about|content\s+about|article\s+about)",
        r"(?:engaging\s+with|following)\s+(?:our|your|the)\s+(?:content|page|profile)",
    ],
}

# GCC-specific patterns
GCC_SIGNAL_PATTERNS: dict[str, list[str]] = {
    "government_tender": [
        r"(?:tender|bid|procurement)\s+(?:from|by|for|issued\s+by)\s+",
        r"(?:munafasat|etimad|kuwait\s+tenderboard)",
        r"(?:adnoc|aramco|dewa|kaust|neom)\s+(?:issues?\s+)?(?:tender|bid|request)",
    ],
    "vision_2030_project": [
        r"(?:vision\s+2030|saudi\s+vision|uae\s+vision|national\s+strategy)",
        r"(?:neom|the\s+line|red\s+sea\s+project|qiddiya|diriyah\s+gate)",
    ],
    "free_zone_setup": [
        r"(?:difc|adgm|dmcc|jafza|kizad|kafd|king\s+abdullah\s+economic\s+city)",
        r"(?:free\s+zone|economic\s+zone|financial\s+centre|financial\s+center)",
    ],
}


def _match_signal(text: str, patterns: dict[str, list[str]]) -> list[tuple[str, float]]:
    """Match text against signal patterns. Returns list of (signal_type, confidence)."""
    matches: list[tuple[str, float]] = []
    text_lower = text.lower()
    for signal_type, pattern_list in patterns.items():
        for pattern in pattern_list:
            if re.search(pattern, text_lower):
                # Confidence based on pattern specificity
                confidence = 0.7 if len(pattern) > 30 else 0.5
                matches.append((signal_type, confidence))
                break  # One match per signal type is enough
    return matches


def detect_signals(
    text: str,
    source: str = "unknown",
    include_gcc: bool = True,
) -> list[IntentSignal]:
    """Detect intent signals from text content.

    Args:
        text: The text to analyze (e.g., job posting, news article, social post).
        source: Where the text came from (e.g., "linkedin", "github", "news").
        include_gcc: Whether to include GCC-specific signal patterns.

    Returns:
        List of detected IntentSignal objects.
    """
    signals: list[IntentSignal] = []

    # Check Tier 1 (Hot) signals
    for signal_type, confidence in _match_signal(text, HOT_SIGNAL_PATTERNS):
        signals.append(
            IntentSignal(
                signal_type=signal_type,
                tier=SignalTier.HOT,
                source=source,
                confidence=confidence,
                recommended_action="Immediate outreach — high intent detected",
                outreach_angle=_get_outreach_angle(signal_type),
            )
        )

    # Check Tier 2 (Warm) signals
    for signal_type, confidence in _match_signal(text, WARM_SIGNAL_PATTERNS):
        signals.append(
            IntentSignal(
                signal_type=signal_type,
                tier=SignalTier.WARM,
                source=source,
                confidence=confidence,
                recommended_action="Add to nurture sequence — interest detected",
                outreach_angle=_get_outreach_angle(signal_type),
            )
        )

    # Check Tier 3 (Nurture) signals
    for signal_type, confidence in _match_signal(text, NURTURE_SIGNAL_PATTERNS):
        signals.append(
            IntentSignal(
                signal_type=signal_type,
                tier=SignalTier.NURTURE,
                source=source,
                confidence=confidence,
                recommended_action="Monitor and engage periodically",
                outreach_angle=_get_outreach_angle(signal_type),
            )
        )

    # Check GCC-specific signals
    if include_gcc:
        for signal_type, confidence in _match_signal(text, GCC_SIGNAL_PATTERNS):
            # GCC signals inherit the tier of the most relevant base signal
            tier = SignalTier.WARM  # Default to warm for GCC-specific
            signals.append(
                IntentSignal(
                    signal_type=f"gcc_{signal_type}",
                    tier=tier,
                    source=source,
                    confidence=confidence,
                    recommended_action="GCC-specific outreach — leverage local presence",
                    outreach_angle=_get_outreach_angle(signal_type),
                )
            )

    return signals


def _get_outreach_angle(signal_type: str) -> str:
    """Map signal type to recommended outreach angle."""
    angles = {
        "funding_round": "Congratulate on funding; position as scaling partner",
        "rfp_published": "Reference RFP directly; demonstrate relevant capabilities",
        "competitor_contract_expiry": "Competitive displacement — highlight differentiation",
        "executive_hire": "Welcome new exec; offer onboarding support",
        "digital_transformation_post": "Share relevant case study or insight",
        "conference_speaker": "Reference their talk; share related content",
        "office_expansion": "Congratulations on growth; offer scalable solutions",
        "job_posting_relevant": "Their hiring signals investment; offer to supplement",
        "industry_report": "Reference the report; share your data/perspective",
        "podcast_appearance": "Reference the episode; share related insights",
        "social_engagement": "Thank them; deepen the relationship",
        "government_tender": "Register on portal; prepare compliant proposal",
        "vision_2030_project": "Align your solution with national strategy goals",
        "free_zone_setup": "New entity = new vendor relationships; early mover advantage",
    }
    return angles.get(signal_type, "Research the signal further before outreach")


async def fetch_linkedin_signals(
    company_name: str,
    api_key: str | None = None,
) -> list[IntentSignal]:
    """Fetch intent signals from LinkedIn (placeholder — requires API access).

    In production, this would use LinkedIn's Marketing API or a third-party
    enrichment tool like Clay, Apollo, or Clearbit to detect signals.

    Returns empty list when API key is not configured.
    """
    api_key = api_key or os.environ.get("LINKEDIN_API_KEY")
    if not api_key:
        return []

    # Placeholder for LinkedIn API integration
    # Would check: recent posts, job changes, company updates, engagement
    return []


async def fetch_news_signals(
    company_name: str,
    days_back: int = 30,
) -> list[IntentSignal]:
    """Fetch intent signals from news articles via web search.

    Uses a lightweight search to find recent news about the company
    and detect intent signals from article text.
    """
    signals: list[IntentSignal] = []

    # Use a simple web search to find recent news
    query = f'"{company_name}" (funding OR hiring OR expansion OR tender OR contract)'
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            # Use a free search API (placeholder — would use a real news API in production)
            resp = await client.get(
                "https://news.google.com/rss/search",
                params={"q": query, "hl": "en", "gl": "AE", "ceid": "AE:en"},
            )
            if resp.status_code == 200:
                # Parse RSS for signal detection
                text = resp.text
                signals.extend(detect_signals(text, source="news"))
        except httpx.HTTPError:
            pass

    return signals


def aggregate_signals(entity_name: str, all_signals: list[IntentSignal]) -> IntentSignalResult:
    """Aggregate multiple signals into a single result with overall tier and score."""
    if not all_signals:
        return IntentSignalResult(entity_name=entity_name)

    # Calculate overall score
    tier_weights = {SignalTier.HOT: 3.0, SignalTier.WARM: 2.0, SignalTier.NURTURE: 1.0}
    score = sum(tier_weights.get(s.tier, 1.0) * s.confidence for s in all_signals)

    # Determine overall tier
    tiers_present = {s.tier for s in all_signals}
    if SignalTier.HOT in tiers_present:
        overall_tier = SignalTier.HOT
    elif SignalTier.WARM in tiers_present:
        overall_tier = SignalTier.WARM
    else:
        overall_tier = SignalTier.NURTURE

    return IntentSignalResult(
        entity_name=entity_name,
        signals=all_signals,
        overall_tier=overall_tier,
        score=score,
    )
