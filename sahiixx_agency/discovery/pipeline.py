"""Discovery pipeline: dedupe, filter, classify, score, register, clone."""

from __future__ import annotations

import asyncio
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from sahiixx_agency.core.models import DiscoveryResult, RepoCategory, RepoNode, RiskLevel
from sahiixx_agency.core.registry import RepoRegistry
from sahiixx_agency.discovery.intent_signals import (
    IntentSignal,
    SignalTier,
    aggregate_signals,
    detect_signals,
)
from sahiixx_agency.discovery.sources import fetch_all_sources

CATEGORY_KEYWORDS: dict[RepoCategory, list[str]] = {
    RepoCategory.SECURITY: ["security", "pentest", "exploit", "vuln", "redteam", "cve", "audit", "scan"],
    RepoCategory.VOICE_AI: ["voice", "speech", "audio", "call", "tts", "stt"],
    RepoCategory.REAL_ESTATE: ["real estate", "property", "listing", "realtor", "dubai"],
    RepoCategory.AGENT_FRAMEWORK: ["agent", "llm", "ai", "swarm", "bot", "autonomous", "gpt", "claude"],
    RepoCategory.MCP_TOOL: ["mcp", "tool", "plugin", "extension"],
    RepoCategory.COOKBOOK: ["prompt", "cookbook", "template", "examples"],
    RepoCategory.OS_PLATFORM: ["os", "platform", "desktop", "workspace"],
}

RISK_OVERRIDES: dict[RepoCategory, RiskLevel] = {
    RepoCategory.SECURITY: RiskLevel.HIGH,
    RepoCategory.AGENT_FRAMEWORK: RiskLevel.MEDIUM,
}


def deduplicate(results: list[DiscoveryResult]) -> list[DiscoveryResult]:
    """Remove duplicate repos, keeping the first mention."""
    seen: set[str] = set()
    out: list[DiscoveryResult] = []
    for result in results:
        key = result.full_name.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(result)
    return out


def classify(result: DiscoveryResult) -> DiscoveryResult:
    """Classify a discovery result by category and risk."""
    text = f"{result.full_name} {result.description}".lower()
    best_category = RepoCategory.UNCATEGORIZED
    best_score = 0
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > best_score:
            best_score = score
            best_category = category
    risk = RISK_OVERRIDES.get(best_category, RiskLevel.LOW)
    if result.stars < 10 and result.source in ("hackernews", "reddit"):
        escalation = {
            RiskLevel.LOW: RiskLevel.MEDIUM,
            RiskLevel.MEDIUM: RiskLevel.HIGH,
            RiskLevel.HIGH: RiskLevel.CRITICAL,
            RiskLevel.CRITICAL: RiskLevel.CRITICAL,
        }
        risk = escalation.get(risk, RiskLevel.MEDIUM)
    return result.model_copy(update={"category": best_category, "risk_level": risk})


def score(result: DiscoveryResult, intent_signals: list[IntentSignal] | None = None) -> float:
    """Score discovery result relevance; higher is better.

    Incorporates intent signals when available — hot signals boost score
    significantly, warm signals provide moderate boost.
    """
    s = float(result.stars)
    if result.category != RepoCategory.UNCATEGORIZED:
        s += 100.0
    if result.language in ("Python", "TypeScript", "JavaScript"):
        s += 20.0

    # Intent signal boost (Gojiberry-style)
    if intent_signals:
        tier_boost = {
            SignalTier.HOT: 500.0,
            SignalTier.WARM: 200.0,
            SignalTier.NURTURE: 50.0,
        }
        for signal in intent_signals:
            s += tier_boost.get(signal.tier, 0.0) * signal.confidence

    return s


def _discovery_result_to_node(result: DiscoveryResult) -> RepoNode:
    owner, _, name = result.full_name.partition("/")
    return RepoNode(
        id=result.full_name.replace("/", "_"),
        name=name,
        owner=owner,
        full_name=result.full_name,
        url=result.url,
        description=result.description,
        stars=result.stars,
        language=result.language,
        category=result.category,
        source=result.source,
        risk_level=result.risk_level,
    )


class DiscoveryPipeline:
    """Runs the full discovery pipeline and registers results."""

    def __init__(
        self,
        data_dir: str = "./data",
        min_stars: int = 50,
        auto_clone: bool = False,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.min_stars = min_stars
        self.auto_clone = auto_clone
        self.discovery_dir = self.data_dir / "discovery"
        self.discovery_dir.mkdir(parents=True, exist_ok=True)

    async def run(self) -> list[RepoNode]:
        """Fetch, dedupe, filter, classify, detect intent signals, and register trending repos."""
        raw = await fetch_all_sources()
        results = [DiscoveryResult.model_validate(r) for r in raw]
        results = deduplicate(results)
        results = [r for r in results if r.stars >= self.min_stars or r.source in ("hackernews", "reddit")]
        results = [classify(r) for r in results]

        # Detect intent signals for each result
        results_with_signals: list[tuple[DiscoveryResult, list[IntentSignal]]] = []
        for r in results:
            text = f"{r.full_name} {r.description}"
            signals = detect_signals(text, source=r.source, include_gcc=True)
            results_with_signals.append((r, signals))

        # Sort by score (now incorporating intent signals)
        results_with_signals.sort(
            key=lambda x: score(x[0], x[1]),
            reverse=True,
        )

        nodes = [_discovery_result_to_node(r) for r, _ in results_with_signals]
        if self.auto_clone:
            for node in nodes[:20]:
                await self._clone(node)
        self._merge_into_registry(nodes)
        self._save_snapshot(results)
        self._save_intent_signals(results_with_signals)
        return nodes

    def _merge_into_registry(self, nodes: list[RepoNode]) -> None:
        """Merge discovered nodes into the canonical registry, avoiding duplicates by id."""
        registry = RepoRegistry(data_dir=str(self.data_dir))
        for node in nodes:
            if registry.get(node.id) is None:
                registry._modules[node.id] = node
        registry.save()

    async def _clone(self, node: RepoNode) -> Path | None:
        target = self.data_dir / "repos" / "trending" / node.owner / node.name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            return target
        proc = await asyncio.to_thread(
            subprocess.run,
            ["git", "clone", "--depth", "1", node.url, str(target)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode == 0:
            return target
        return None

    def _save_snapshot(self, results: list[DiscoveryResult]) -> None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = self.discovery_dir / f"{date_str}.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for r in results:
                f.write(r.model_dump_json() + "\n")

    def _save_intent_signals(
        self,
        results_with_signals: list[tuple[DiscoveryResult, list[IntentSignal]]],
    ) -> None:
        """Save intent signals snapshot for downstream consumption."""
        hot_signals = [
            (r, signals)
            for r, signals in results_with_signals
            if any(s.tier == SignalTier.HOT for s in signals)
        ]
        if not hot_signals:
            return

        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = self.discovery_dir / f"{date_str}-intent-signals.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for r, signals in hot_signals:
                result = aggregate_signals(r.full_name, signals)
                f.write(result.model_dump_json() + "\n")
