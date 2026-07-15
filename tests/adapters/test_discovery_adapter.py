"""Tests for the DiscoveryAdapter (GitHub trending / intel scout)."""

from __future__ import annotations

import pytest

from sahiixx_agency.adapters.discovery_adapter import DiscoveryAdapter


@pytest.mark.asyncio
async def test_simulate_returns_sample_repos():
    adapter = DiscoveryAdapter()
    result = await adapter.execute({"simulate": True, "report_type": "trending"})
    assert result["status"] == "simulated"
    assert result["report_type"] == "trending"
    assert result["repos_found"] == len(result["repos"])
    assert result["repos_found"] > 0
    for repo in result["repos"]:
        assert "name" in repo and "stars" in repo


@pytest.mark.asyncio
async def test_execute_success_with_mocked_search(monkeypatch):
    adapter = DiscoveryAdapter()

    async def fake_search(self, query, per_page):  # noqa: ARG001
        return [
            {
                "name": "cool-agent",
                "owner": {"login": "octocat"},
                "stargazers_count": 512,
                "language": "Python",
                "html_url": "https://github.com/octocat/cool-agent",
                "description": "An agent framework",
            }
        ]

    monkeypatch.setattr(DiscoveryAdapter, "_search", fake_search)
    result = await adapter.execute({"report_type": "trending", "min_stars": 100})
    assert result["status"] == "success"
    assert result["repos_found"] == 1
    repo = result["repos"][0]
    assert repo["name"] == "cool-agent"
    assert repo["owner"] == "octocat"
    assert repo["stars"] == 512


@pytest.mark.asyncio
async def test_execute_falls_back_on_search_error(monkeypatch):
    adapter = DiscoveryAdapter()

    async def boom(self, query, per_page):  # noqa: ARG001
        raise RuntimeError("GitHub search returned HTTP 403")

    monkeypatch.setattr(DiscoveryAdapter, "_search", boom)
    result = await adapter.execute({"report_type": "trending"})
    assert result["status"] == "fallback"
    assert "error" in result
    assert result["repos_found"] > 0  # fallback sample still returned


@pytest.mark.asyncio
async def test_hidden_gems_report_type(monkeypatch):
    adapter = DiscoveryAdapter()
    captured = {}

    async def capture_search(self, query, per_page):  # noqa: ARG001
        captured["query"] = query
        captured["per_page"] = per_page
        return []

    monkeypatch.setattr(DiscoveryAdapter, "_search", capture_search)
    result = await adapter.execute({"report_type": "hidden_gems"})
    assert result["status"] == "success"
    assert "stars:100..1000" in captured["query"]
    assert captured["per_page"] == 15
