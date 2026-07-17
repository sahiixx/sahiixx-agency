"""Tests for the web intel adapter."""

from __future__ import annotations

import pytest

from sahiixx_agency.adapters.web_intel import WebIntelAdapter


@pytest.fixture
def adapter(tmp_path):
    return WebIntelAdapter(clone_base_dir=str(tmp_path))


@pytest.mark.asyncio
async def test_web_intel_requires_url(adapter):
    result = await adapter.execute({})
    assert result["status"] == "failed"
    assert "No URL" in result["error"]


@pytest.mark.asyncio
async def test_web_intel_extracts_projects(monkeypatch):
    html = """
    <html><head><title>Profile</title></head>
    <body>
      <h1>Profile</h1>
      <p><strong>project-alpha</strong> A test project</p>
      <p><strong>project-beta</strong> Another test project</p>
    </body></html>
    """

    async def fake_get(*args, **kwargs):
        import httpx

        return httpx.Response(200, text=html, request=httpx.Request("GET", "https://example.com"))

    monkeypatch.setattr("httpx.AsyncClient.get", fake_get)

    adapter = WebIntelAdapter(clone_base_dir="/tmp")
    result = await adapter.execute({"url": "https://example.com"})
    assert result["status"] == "success"
    assert result["url"] == "https://example.com"
    assert result["title"] == "Profile"
    names = {p["name"] for p in result["projects"]}
    assert "project-alpha" in names
    assert "project-beta" in names


@pytest.mark.asyncio
async def test_web_intel_handles_fetch_error(monkeypatch):
    async def fake_get(*args, **kwargs):
        raise httpx.ConnectError("Connection failed")

    monkeypatch.setattr("httpx.AsyncClient.get", fake_get)

    adapter = WebIntelAdapter(clone_base_dir="/tmp")
    result = await adapter.execute({"url": "https://example.com"})
    assert result["status"] == "failed"
    assert "Fetch failed" in result["error"]
