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
