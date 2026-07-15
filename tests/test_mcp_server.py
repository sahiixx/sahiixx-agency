"""Tests for the MCP server."""
from __future__ import annotations

import httpx
import pytest

from sahiixx_agency.mcp_server import main as mcp_main


@pytest.mark.asyncio
async def test_health_endpoint_returns_ok() -> None:
    """The SSE app should expose a /health route returning 200."""
    app = mcp_main.mcp.sse_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_load_config_from_file(tmp_path) -> None:
    """``_load_config`` should read OPA_CONFIG when the file exists."""
    config_path = tmp_path / "agency.yaml"
    config_path.write_text(
        'github_username: "test-user"\napi_port: 9999\nrouting_rules: []\n',
        encoding="utf-8",
    )

    original_config = mcp_main._engine
    try:
        mcp_main._engine = None
        import os

        old = os.environ.get("OPA_CONFIG")
        os.environ["OPA_CONFIG"] = str(config_path)
        config = mcp_main._load_config()
        if old is None:
            os.environ.pop("OPA_CONFIG", None)
        else:
            os.environ["OPA_CONFIG"] = old
        assert config.github_username == "test-user"
        assert config.api_port == 9999
    finally:
        mcp_main._engine = original_config


def test_load_config_defaults_when_missing() -> None:
    """``_load_config`` should fall back to defaults when the file is absent."""
    import os

    original_config = mcp_main._engine
    try:
        mcp_main._engine = None
        old = os.environ.get("OPA_CONFIG")
        os.environ["OPA_CONFIG"] = "/nonexistent/agency.yaml"
        config = mcp_main._load_config()
        if old is None:
            os.environ.pop("OPA_CONFIG", None)
        else:
            os.environ["OPA_CONFIG"] = old
        assert config.github_username == "sahiixx"
    finally:
        mcp_main._engine = original_config


@pytest.mark.asyncio
async def test_discover_repos_tool_simulate() -> None:
    """The discover_repos MCP tool should return a simulated discovery report."""
    import json

    result = await mcp_main.discover_repos(report_type="trending", simulate=True)
    data = json.loads(result)
    assert data["status"] == "simulated"
    assert data["report_type"] == "trending"
    assert data["repos_found"] == len(data["repos"])
    assert data["repos_found"] > 0


@pytest.mark.asyncio
async def test_discover_repos_tool_parses_languages(monkeypatch) -> None:
    """discover_repos should split the comma-separated languages arg into a list."""
    import json

    from sahiixx_agency.adapters.discovery_adapter import DiscoveryAdapter

    captured: dict = {}

    async def fake_execute(self, payload):  # noqa: ARG001
        captured.update(payload)
        return {"status": "success", "report_type": payload["report_type"], "repos_found": 0, "repos": []}

    monkeypatch.setattr(DiscoveryAdapter, "execute", fake_execute)
    result = await mcp_main.discover_repos(report_type="trending", languages="python, rust")
    data = json.loads(result)
    assert data["status"] == "success"
    assert captured.get("languages") == ["python", "rust"]
