"""Quick script to check each discovery source."""
from __future__ import annotations

import asyncio

from sahiixx_agency.discovery.intent_signals import detect_signals, aggregate_signals, SignalTier
from sahiixx_agency.discovery.sources import (
    fetch_github_trending,
    fetch_github_velocity,
    fetch_hackernews_repos,
    fetch_reddit_repos,
)


async def main() -> None:
    print("=== GitHub Trending ===")
    trending = await fetch_github_trending()
    print(f"  Found {len(trending)} repos")
    for r in trending[:5]:
        print(f"    {r['full_name']} ({r['stars']} stars)")

    print("\n=== GitHub Velocity ===")
    velocity = await fetch_github_velocity()
    print(f"  Found {len(velocity)} repos")
    for r in velocity[:5]:
        print(f"    {r['full_name']} ({r['stars']} stars)")

    print("\n=== HackerNews ===")
    hn = await fetch_hackernews_repos()
    print(f"  Found {len(hn)} repos")
    for r in hn[:5]:
        desc = r["description"][:60] if r["description"] else "(no description)"
        print(f"    {r['full_name']} - {desc}")

    print("\n=== Reddit ===")
    reddit = await fetch_reddit_repos()
    print(f"  Found {len(reddit)} repos")
    for r in reddit[:5]:
        desc = r["description"][:60] if r["description"] else "(no description)"
        print(f"    {r['full_name']} - {desc}")

    # Test intent signals on a sample
    print("\n=== Intent Signal Detection (sample) ===")
    sample_texts = [
        "StartupX raised a Series B of $45M led by Sequoia Capital",
        "Company appoints new CTO from Google Cloud",
        "ADNOC issues tender for digital platform modernization",
        "CEO appeared on the TechCrunch podcast discussing AI adoption",
        "Firm opens new office in Dubai, hiring 50 engineers",
    ]
    for text in sample_texts:
        signals = detect_signals(text, source="test")
        tier_counts = {}
        for s in signals:
            tier_counts[s.tier.value] = tier_counts.get(s.tier.value, 0) + 1
        result = aggregate_signals("sample", signals)
        print(f"  Text: {text[:50]}...")
        print(f"    Signals: {len(signals)} | Tiers: {tier_counts} | Score: {result.score:.1f} | Overall: {result.overall_tier.value}")
        for s in signals:
            print(f"      - {s.signal_type} ({s.tier.value}, {s.confidence:.1f}): {s.outreach_angle[:50]}")


if __name__ == "__main__":
    asyncio.run(main())
