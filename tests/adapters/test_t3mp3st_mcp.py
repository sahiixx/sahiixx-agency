"""Tests for the T3MP3ST MCP adapter."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

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
async def test_mcp_adapter_reuses_validation_before_fallback(t3mp3st_module, tmp_path):
    adapter = T3mp3stMcpAdapter(clone_base_dir=str(tmp_path))
    result = await adapter.run(t3mp3st_module, {"target": "localhost"})
    assert result["status"] == "validation_error"
    assert result["error_code"] == "blocked_target"


def test_build_mcp_env_sanitizes_environment(t3mp3st_adapter, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "super_secret")
    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.setenv("NODE_OPTIONS", "--max-old-space-size=4096")
    monkeypatch.setenv("NPM_CONFIG_REGISTRY", "https://registry.npmjs.org")

    env = {
        "T3MP3ST_TARGET": "example.com",
        "T3MP3ST_FULL_ARSENAL": "0",
        "T3MP3ST_EGRESS_POLICY": "scoped",
    }

    run_env = t3mp3st_adapter._build_mcp_env(env)

    assert run_env.get("T3MP3ST_TARGET") == "example.com"
    assert run_env.get("T3MP3ST_FULL_ARSENAL") == "0"
    assert run_env.get("T3MP3ST_EGRESS_POLICY") == "scoped"
    assert run_env.get("PATH") == "/usr/bin"
    assert run_env.get("NODE_OPTIONS") == "--max-old-space-size=4096"
    assert run_env.get("NPM_CONFIG_REGISTRY") == "https://registry.npmjs.org"
    assert "GITHUB_TOKEN" not in run_env


@pytest.mark.asyncio
async def test_mcp_adapter_sanitizes_subprocess_env(
    t3mp3st_module, t3mp3st_adapter, monkeypatch, tmp_path
):
    captured_params: list[Any] = []

    @asynccontextmanager
    async def fake_stdio_client(params) -> AsyncIterator[tuple[Any, Any]]:
        captured_params.append(params)
        yield None, None

    class FakeSession:
        async def initialize(self):
            return None

        async def list_tools(self):
            class ToolsResult:
                tools = []

            return ToolsResult()

    @asynccontextmanager
    async def fake_client_session(read, write) -> AsyncIterator[Any]:
        yield FakeSession()

    monkeypatch.setattr(
        "sahiixx_agency.adapters.security.t3mp3st_mcp.stdio_client",
        fake_stdio_client,
    )
    monkeypatch.setattr(
        "sahiixx_agency.adapters.security.t3mp3st_mcp.ClientSession",
        fake_client_session,
    )

    async def fake_clone(node):
        repo_path = tmp_path / node.owner / node.name
        repo_path.mkdir(parents=True, exist_ok=True)
        (repo_path / "mcp-server.js").write_text("// mcp server stub")
        return repo_path

    monkeypatch.setattr(t3mp3st_adapter.runner.clone_manager, "clone", fake_clone)
    monkeypatch.setenv("GITHUB_TOKEN", "super_secret")
    monkeypatch.setenv("PATH", "/usr/bin")

    result = await t3mp3st_adapter.run(t3mp3st_module, {"target": "example.com"})

    assert result["fallback_reason"] == "no_matching_mcp_tool"
    assert len(captured_params) == 1
    params = captured_params[0]
    assert "GITHUB_TOKEN" not in params.env
    assert params.env.get("T3MP3ST_TARGET") == "example.com"
    assert params.env.get("PATH") == "/usr/bin"
