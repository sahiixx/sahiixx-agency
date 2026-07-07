"""Tests for the MCP server."""

from __future__ import annotations

import httpx
import pytest

from sahiixx_agency.mcp_server.main import mcp


@pytest.mark.asyncio
async def test_health_endpoint_returns_ok() -> None:
    """The SSE app should expose a /health route returning 200."""
    app = mcp.sse_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
