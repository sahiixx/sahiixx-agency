from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from sahiixx_agency.adapters.agent_framework.letta_code_adapter import (
    LettaCodeAdapter,
    LettaCodeResult,
    run_letta_code,
)
from sahiixx_agency.adapters.agents.runner import AgentAdapter, run_agent_module
from sahiixx_agency.adapters.mcp.runner import McpAdapter, run_mcp_module
from sahiixx_agency.adapters.realestate.runner import RealEstateAdapter, run_realestate_module
from sahiixx_agency.adapters.voice.runner import VoiceAdapter, run_voice_module
from sahiixx_agency.core.models import RepoNode
from sahiixx_agency.core.security import NetworkPolicy


def _make_node(name: str) -> RepoNode:
    return RepoNode(
        id=name,
        name=name,
        owner="test",
        full_name=f"test/{name}",
        url=f"https://github.com/test/{name}",
    )


def _fake_clone_manager(path: Path):
    """Return a mock CloneManager that returns the given path without cloning."""
    mock = MagicMock()
    mock.clone = AsyncMock(return_value=path)
    return mock


# ─── Thin adapter stubs (agents, mcp, realestate, voice) ───────────────────

@pytest.mark.asyncio
async def test_agent_adapter_sets_timeout_and_delegates(tmp_path, monkeypatch):
    """AgentAdapter should default timeout to 120 and delegate to BaseAdapter."""
    repo = tmp_path / "agent-repo"
    repo.mkdir()
    (repo / "main.py").write_text("print('agent')")

    node = _make_node("agent-repo")
    adapter = AgentAdapter()
    adapter.runner.clone_manager = _fake_clone_manager(repo)

    def fake_run(cmd, **kwargs):
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = "agent output"
        mock.stderr = ""
        return mock

    monkeypatch.setattr("sahiixx_agency.core.runner.subprocess.run", fake_run)
    result = await adapter.run(node, {})
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_agent_adapter_respects_custom_timeout(tmp_path, monkeypatch):
    """AgentAdapter should use the timeout from payload when provided."""
    repo = tmp_path / "agent-repo"
    repo.mkdir()
    (repo / "main.py").write_text("print('agent')")

    node = _make_node("agent-repo")
    adapter = AgentAdapter()
    adapter.runner.clone_manager = _fake_clone_manager(repo)

    captured: dict[str, Any] = {}

    def fake_run(cmd, **kwargs):
        captured["timeout"] = kwargs.get("timeout")
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = ""
        mock.stderr = ""
        return mock

    monkeypatch.setattr("sahiixx_agency.core.runner.subprocess.run", fake_run)
    await adapter.run(node, {"timeout": 300})
    assert captured["timeout"] == 300


@pytest.mark.asyncio
async def test_mcp_adapter_sets_timeout(tmp_path, monkeypatch):
    """McpAdapter should default timeout to 90."""
    repo = tmp_path / "mcp-repo"
    repo.mkdir()
    (repo / "main.py").write_text("print('mcp')")

    node = _make_node("mcp-repo")
    adapter = McpAdapter()
    adapter.runner.clone_manager = _fake_clone_manager(repo)

    def fake_run(cmd, **kwargs):
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = "mcp output"
        mock.stderr = ""
        return mock

    monkeypatch.setattr("sahiixx_agency.core.runner.subprocess.run", fake_run)
    result = await adapter.run(node, {})
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_realestate_adapter_sets_timeout(tmp_path, monkeypatch):
    """RealEstateAdapter should default timeout to 120."""
    repo = tmp_path / "realestate-repo"
    repo.mkdir()
    (repo / "main.py").write_text("print('realestate')")

    node = _make_node("realestate-repo")
    adapter = RealEstateAdapter()
    adapter.runner.clone_manager = _fake_clone_manager(repo)

    def fake_run(cmd, **kwargs):
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = "realestate output"
        mock.stderr = ""
        return mock

    monkeypatch.setattr("sahiixx_agency.core.runner.subprocess.run", fake_run)
    result = await adapter.run(node, {})
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_voice_adapter_sets_timeout(tmp_path, monkeypatch):
    """VoiceAdapter should default timeout to 90."""
    repo = tmp_path / "voice-repo"
    repo.mkdir()
    (repo / "main.py").write_text("print('voice')")

    node = _make_node("voice-repo")
    adapter = VoiceAdapter()
    adapter.runner.clone_manager = _fake_clone_manager(repo)

    def fake_run(cmd, **kwargs):
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = "voice output"
        mock.stderr = ""
        return mock

    monkeypatch.setattr("sahiixx_agency.core.runner.subprocess.run", fake_run)
    result = await adapter.run(node, {})
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_voice_adapter_not_runnable_when_no_entrypoint(tmp_path):
    """VoiceAdapter should return not_runnable when repo has no recognized entrypoint."""
    repo = tmp_path / "voice-empty"
    repo.mkdir()
    # No main.py, package.json, or .sh files

    node = _make_node("voice-empty")
    adapter = VoiceAdapter()
    adapter.runner.clone_manager = _fake_clone_manager(repo)
    result = await adapter.run(node, {})
    assert result["status"] == "not_runnable"


def test_run_agent_module_sync_wrapper():
    """run_agent_module should be a synchronous wrapper around AgentAdapter."""
    node = _make_node("agent-sync")
    with pytest.raises(RuntimeError):
        run_agent_module(node, {})


def test_run_mcp_module_sync_wrapper():
    """run_mcp_module should be a synchronous wrapper around McpAdapter."""
    node = _make_node("mcp-sync")
    with pytest.raises(RuntimeError):
        run_mcp_module(node, {})


def test_run_realestate_module_sync_wrapper():
    """run_realestate_module should be a synchronous wrapper around RealEstateAdapter."""
    node = _make_node("realestate-sync")
    with pytest.raises(RuntimeError):
        run_realestate_module(node, {})


def test_run_voice_module_sync_wrapper():
    """run_voice_module should be a synchronous wrapper around VoiceAdapter."""
    node = _make_node("voice-sync")
    with pytest.raises(RuntimeError):
        run_voice_module(node, {})


# ─── Letta Code adapter ──────────────────────────────────────────────────────


def test_letta_code_adapter_infer_persona():
    """LettaCodeAdapter should infer persona from brief keywords."""
    adapter = LettaCodeAdapter(repo_dir="/tmp")
    assert adapter._infer_persona("Write a blog post about AI") == "writer"
    assert adapter._infer_persona("Debug this API code") == "coder"
    assert adapter._infer_persona("Research quantum computing") == "researcher"
    assert adapter._infer_persona("How to learn Python") == "tutorial"
    assert adapter._infer_persona("Something vague") == "default"


def test_letta_code_adapter_write_brief(tmp_path):
    """LettaCodeAdapter._write_brief should create brief.txt and persona.txt."""
    adapter = LettaCodeAdapter(repo_dir=str(tmp_path))
    project_dir = tmp_path / "projects" / "test_project"
    adapter._write_brief(project_dir, "Build an agent", "coder")
    assert (project_dir / "brief.txt").read_text() == "Build an agent"
    assert (project_dir / "persona.txt").read_text() == "coder"


def test_letta_code_adapter_simulate(tmp_path):
    """LettaCodeAdapter._simulate should return a deterministic result."""
    adapter = LettaCodeAdapter(repo_dir=str(tmp_path))
    project_dir = tmp_path / "projects" / "sim"
    result = adapter._simulate(project_dir, "test brief", "coder")
    assert result.ok is True
    assert result.status == "simulated"
    assert result.persona == "coder"
    assert result.brief == "test brief"
    assert "SIMULATED" in result.stdout


def test_letta_code_adapter_dispatch_simulate(tmp_path):
    """LettaCodeAdapter.dispatch with simulate=True should return simulated result."""
    adapter = LettaCodeAdapter(repo_dir=str(tmp_path))
    result = adapter.dispatch("Build an API", simulate=True)
    assert result.ok is True
    assert result.status == "simulated"
    assert result.persona == "coder"


def test_letta_code_adapter_dispatch_no_brief():
    """LettaCodeAdapter.dispatch should handle empty brief gracefully."""
    adapter = LettaCodeAdapter(repo_dir="/tmp")
    result = adapter.dispatch("", simulate=True)
    assert result.ok is True
    assert result.persona == "default"


def test_letta_code_adapter_build_command_python_fallback(tmp_path):
    """When no letta.js or package.json exists, _build_command should fall back to python."""
    adapter = LettaCodeAdapter(repo_dir=str(tmp_path))
    project_dir = tmp_path / "projects" / "test"
    cmd = adapter._build_command(project_dir, "coder")
    assert cmd[0] == "python"


def test_letta_code_adapter_build_command_bun_when_package_json(tmp_path):
    """When package.json exists, _build_command should use bun/npx."""
    adapter = LettaCodeAdapter(repo_dir=str(tmp_path))
    (tmp_path / "package.json").write_text('{"name": "letta"}')
    project_dir = tmp_path / "projects" / "test"
    cmd = adapter._build_command(project_dir, "coder")
    assert cmd[2] == "run"
    assert cmd[3] == "letta"


def test_letta_code_adapter_run_subprocess_success(tmp_path, monkeypatch):
    """LettaCodeAdapter._run_subprocess should capture stdout and returncode."""
    adapter = LettaCodeAdapter(repo_dir=str(tmp_path))
    project_dir = tmp_path / "projects" / "test"

    def fake_run(cmd, **kwargs):
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = "success output"
        mock.stderr = ""
        return mock

    monkeypatch.setattr("subprocess.run", fake_run)
    result = adapter._run_subprocess(project_dir, ["echo", "hello"])
    assert result.ok is True
    assert result.returncode == 0
    assert result.stdout == "success output"


def test_letta_code_adapter_run_subprocess_timeout(tmp_path, monkeypatch):
    """LettaCodeAdapter._run_subprocess should handle timeout gracefully."""
    import subprocess as sp

    adapter = LettaCodeAdapter(repo_dir=str(tmp_path), timeout=1)
    project_dir = tmp_path / "projects" / "test"

    def fake_run(cmd, **kwargs):
        raise sp.TimeoutExpired(cmd="echo", timeout=1)

    monkeypatch.setattr("subprocess.run", fake_run)
    result = adapter._run_subprocess(project_dir, ["echo", "hello"])
    assert result.ok is False
    assert result.status == "timeout"


def test_letta_code_adapter_run_subprocess_exception(tmp_path, monkeypatch):
    """LettaCodeAdapter._run_subprocess should handle generic exceptions."""
    adapter = LettaCodeAdapter(repo_dir=str(tmp_path))
    project_dir = tmp_path / "projects" / "test"

    def fake_run(cmd, **kwargs):
        raise OSError("something broke")

    monkeypatch.setattr("subprocess.run", fake_run)
    result = adapter._run_subprocess(project_dir, ["echo", "hello"])
    assert result.ok is False
    assert result.status == "exception"
    assert "something broke" in result.stderr


def test_letta_code_adapter_network_policy_blocks(tmp_path):
    """LettaCodeAdapter._check_network_policy should block disallowed hosts."""
    adapter = LettaCodeAdapter(repo_dir=str(tmp_path))
    policy = NetworkPolicy(allowlist=["github.com"], default_allow=False)
    adapter.network_policy = policy

    node = RepoNode(
        id="letta",
        name="letta",
        owner="test",
        full_name="test/letta",
        url="https://github.com/test/letta",
        external_hosts=["evil.com"],
    )
    with pytest.raises(RuntimeError, match="Network policy blocks"):
        adapter._check_network_policy(node)


def test_letta_code_adapter_network_policy_allows(tmp_path):
    """LettaCodeAdapter._check_network_policy should allow whitelisted hosts."""
    adapter = LettaCodeAdapter(repo_dir=str(tmp_path))
    policy = NetworkPolicy(allowlist=["github.com"], default_allow=False)
    adapter.network_policy = policy

    node = RepoNode(
        id="letta",
        name="letta",
        owner="test",
        full_name="test/letta",
        url="https://github.com/test/letta",
        external_hosts=["api.github.com"],
    )
    # Should not raise
    adapter._check_network_policy(node)


@pytest.mark.asyncio
async def test_letta_code_adapter_async_run_simulate(tmp_path):
    """LettaCodeAdapter.run should work via the async interface with simulate=True."""
    adapter = LettaCodeAdapter(repo_dir=str(tmp_path))
    node = RepoNode(
        id="letta",
        name="letta",
        owner="letta-ai",
        full_name="letta-ai/letta-code",
        url="https://github.com/letta-ai/letta-code",
    )
    result = await adapter.run(node, {"brief": "Build an API", "simulate": True})
    assert result["status"] == "simulated"
    assert result["brief"] == "Build an API"
    assert result["persona"] == "coder"


@pytest.mark.asyncio
async def test_letta_code_adapter_async_run_no_brief(tmp_path):
    """LettaCodeAdapter.run should fail gracefully when no brief is provided."""
    adapter = LettaCodeAdapter(repo_dir=str(tmp_path))
    node = RepoNode(
        id="letta",
        name="letta",
        owner="letta-ai",
        full_name="letta-ai/letta-code",
        url="https://github.com/letta-ai/letta-code",
    )
    result = await adapter.run(node, {})
    assert result["status"] == "failed"
    assert "No brief provided" in result["error"]


def test_letta_code_result_post_init():
    """LettaCodeResult should set status from ok in post_init."""
    result = LettaCodeResult(
        ok=True,
        brief="test",
        persona="coder",
        command="echo hello",
        returncode=0,
        stdout="",
        stderr="",
        cwd="/tmp",
        project_dir="/tmp/proj",
    )
    assert result.status == "success"

    result_fail = LettaCodeResult(
        ok=False,
        brief="test",
        persona="coder",
        command="echo hello",
        returncode=1,
        stdout="",
        stderr="error",
        cwd="/tmp",
        project_dir="/tmp/proj",
    )
    assert result_fail.status == "failed"


def test_run_letta_code_convenience_function():
    """run_letta_code should be a convenience wrapper around LettaCodeAdapter.dispatch."""
    result = run_letta_code("Build an API", repo_dir="C:/Users/sahii/THIS_DOES_NOT_EXIST_99999")
    assert result.ok is True
    assert result.status == "simulated"
    assert result.persona == "coder"


def test_letta_code_adapter_fallback_on_failure(tmp_path, monkeypatch):
    """When subprocess fails and fallback_on_failure=True, dispatch should return simulation."""
    adapter = LettaCodeAdapter(repo_dir=str(tmp_path), fallback_on_failure=True)
    (tmp_path / "package.json").write_text('{"name": "letta"}')

    def fake_run(cmd, **kwargs):
        mock = MagicMock()
        mock.returncode = 1
        mock.stdout = ""
        mock.stderr = "command not found"
        return mock

    monkeypatch.setattr("subprocess.run", fake_run)
    result = adapter.dispatch("Build an API")
    assert result.status == "simulated"
    assert result.metadata.get("original_error") == "command not found"


def test_letta_code_adapter_project_name_sanitization():
    """LettaCodeAdapter.dispatch should sanitize project names from briefs."""
    adapter = LettaCodeAdapter(repo_dir="/tmp")
    result = adapter.dispatch("Hello world!!!", simulate=True)
    assert "Hello_world" in result.project_dir or "hello_world" in result.project_dir.lower()


def test_letta_code_adapter_find_bun_prefers_bun():
    """LettaCodeAdapter._find_bun should return ['bun'] when bun is available."""
    adapter = LettaCodeAdapter(repo_dir="/tmp")
    result = adapter._find_bun()
    assert result == ["bun"] or result == ["npx", "bun"]


def test_letta_code_adapter_persona_keywords():
    """LettaCodeAdapter.PERSONAS should contain the expected personas."""
    adapter = LettaCodeAdapter(repo_dir="/tmp")
    assert "coder" in adapter.PERSONAS
    assert "researcher" in adapter.PERSONAS
    assert "writer" in adapter.PERSONAS
    assert "tutorial" in adapter.PERSONAS
    assert "default" in adapter.PERSONAS
