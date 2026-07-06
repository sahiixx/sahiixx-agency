"""Tests for the HTML-Anything adapter."""

from __future__ import annotations

import pytest

from sahiixx_agency.adapters.design.html_anything_adapter import HtmlAnythingAdapter


def test_adapter_infers_surface() -> None:
    adapter = HtmlAnythingAdapter(repo_dir=".")
    assert adapter._infer_surface("create a pitch deck") == "deck"
    assert adapter._infer_surface("landing page for my startup") == "web_prototype"
    assert adapter._infer_surface("monthly report") == "report"


def test_adapter_dispatch_requires_brief() -> None:
    import asyncio

    from sahiixx_agency.core.models import RepoNode

    adapter = HtmlAnythingAdapter(repo_dir=".")
    node = RepoNode(
        id="html_anything",
        name="html-anything",
        owner="nexu-io",
        full_name="nexu-io/html-anything",
        url="https://github.com/nexu-io/html-anything",
    )
    result = asyncio.run(adapter.run(node, {}))
    assert result["status"] == "failed"
    assert "No brief provided" in result["error"]


def test_adapter_simulate_returns_plan() -> None:
    import asyncio

    from sahiixx_agency.core.models import RepoNode

    adapter = HtmlAnythingAdapter(repo_dir=".")
    node = RepoNode(
        id="html_anything",
        name="html-anything",
        owner="nexu-io",
        full_name="nexu-io/html-anything",
        url="https://github.com/nexu-io/html-anything",
    )
    result = asyncio.run(adapter.run(node, {"brief": " cinematic landing page", "surface": "landing_page", "simulate": True}))
    assert result["status"] == "simulated"
    assert result["surface"] == "landing_page"
    assert "localhost:3000" in result["stdout"]


@pytest.mark.asyncio
async def test_adapter_run_async() -> None:
    from sahiixx_agency.core.models import RepoNode

    adapter = HtmlAnythingAdapter(repo_dir=".")
    node = RepoNode(
        id="html_anything",
        name="html-anything",
        owner="nexu-io",
        full_name="nexu-io/html-anything",
        url="https://github.com/nexu-io/html-anything",
    )
    result = await adapter.run(node, {"brief": "magazine cover", "surface": "magazine", "simulate": True})
    assert result["status"] == "simulated"
    assert result["surface"] == "magazine"
