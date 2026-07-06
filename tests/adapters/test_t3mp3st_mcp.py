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
        owner="elder-plinius",
        full_name="elder-plinius/T3MP3ST",
        url="https://github.com/elder-plinius/T3MP3ST",
        clone_url="https://github.com/elder-plinius/T3MP3ST.git",
    )


@pytest.fixture
def t3mp3st_adapter(tmp_path):
    return T3mp3stMcpAdapter(clone_base_dir=str(tmp_path), approval_token="secret")


@pytest.mark.asyncio
async def test_mcp_adapter_falls_back_when_server_unavailable(
    t3mp3st_module, t3mp3st_adapter, monkeypatch, tmp_path
):
    async def fake_clone(node):
        repo_path = tmp_path / node.owner / node.name
        repo_path.mkdir(parents=True, exist_ok=True)
        return repo_path

    monkeypatch.setattr(t3mp3st_adapter.runner.clone_manager, "clone", fake_clone)

    async def fake_subprocess_run(self, module, payload):
        return {"status": "success", "source": "subprocess", "module": module.name}

    monkeypatch.setattr("sahiixx_agency.adapters.base.BaseAdapter.run", fake_subprocess_run)

    result = await t3mp3st_adapter.run(t3mp3st_module, {"target": "example.com"})
    assert result["status"] == "success"
    assert result["source"] == "subprocess"
    assert result["fallback_reason"] == "mcp_server_not_found"


@pytest.mark.asyncio
async def test_mcp_adapter_reuses_validation_before_fallback(t3mp3st_module):
    adapter = T3mp3stMcpAdapter()
    result = await adapter.run(t3mp3st_module, {"target": "localhost"})
    assert result["status"] == "validation_error"
    assert result["error_code"] == "blocked_target"
