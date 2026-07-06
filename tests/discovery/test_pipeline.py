from __future__ import annotations

import pytest

from sahiixx_agency.core.models import DiscoveryResult, RepoCategory, RiskLevel
from sahiixx_agency.discovery.pipeline import DiscoveryPipeline, classify, deduplicate


def test_deduplicate_keeps_first() -> None:
    results = [
        DiscoveryResult(full_name="a/b", url="https://github.com/a/b", source="github"),
        DiscoveryResult(full_name="a/b", url="https://github.com/a/b", source="reddit"),
    ]
    out = deduplicate(results)
    assert len(out) == 1
    assert out[0].source == "github"


def test_classify_security_repo() -> None:
    result = classify(DiscoveryResult(full_name="x/pentest-tool", url="https://github.com/x/pentest-tool"))
    assert result.category == RepoCategory.SECURITY
    assert result.risk_level == RiskLevel.HIGH


def test_classify_agent_framework() -> None:
    result = classify(DiscoveryResult(full_name="x/awesome-llm-agent", url="https://github.com/x/awesome-llm-agent"))
    assert result.category == RepoCategory.AGENT_FRAMEWORK


@pytest.mark.asyncio
async def test_pipeline_filters_by_min_stars(monkeypatch):
    async def fake_sources():
        return [
            DiscoveryResult(full_name="a/b", url="https://github.com/a/b", stars=10),
            DiscoveryResult(full_name="c/d", url="https://github.com/c/d", stars=100),
        ]

    monkeypatch.setattr("sahiixx_agency.discovery.pipeline.fetch_all_sources", fake_sources)
    pipeline = DiscoveryPipeline(data_dir="./data_test", min_stars=50)
    nodes = await pipeline.run()
    assert len(nodes) == 1
    assert nodes[0].name == "d"
