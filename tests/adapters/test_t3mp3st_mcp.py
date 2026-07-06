"""Tests for the T3MP3ST MCP adapter."""

from __future__ import annotations

import pytest

from sahiixx_agency.adapters.security.t3mp3st_mcp import T3mp3stMcpAdapter
from sahiixx_agency.core.models import RepoNode


@pytest.fixture
def t3mp3st_module(tmp_path):
    return RepoNode(
        id="T3MP3ST",
        name="T3MP3ST",
        full_name="elder-plinius/T3MP3ST",
        url="https://github.com/elder-plinius/T3MP3ST",
        clone_url="https://github.com/elder-plinius/T3MP3ST.git",
    )


@pytest.mark.asyncio
async def test_mcp_adapter_falls_back_when_server_unavailable(t3mp3st_module, monkeypatch):
    adapter = T3mp3stMcpAdapter(approval_token="secret")

    async def fake_subprocess_run(self, module, payload):
        return {"status": "success", "source": "subprocess", "module": module.name}

    monkeypatch.setattr("sahiixx_agency.adapters.base.BaseAdapter.run", fake_subprocess_run)

    result = await adapter.run(t3mp3st_module, {"target": "example.com"})
    assert result["status"] == "success"
    assert result["source"] == "subprocess"
    assert result["fallback_reason"] == "mcp_server_not_found"


@pytest.mark.asyncio
async def test_mcp_adapter_reuses_validation_before_fallback(t3mp3st_module):
    adapter = T3mp3stMcpAdapter()
    result = await adapter.run(t3mp3st_module, {"target": "localhost"})
    assert result["status"] == "validation_error"
    assert result["error_code"] == "blocked_target"
