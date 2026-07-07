from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from sahiixx_agency.adapters.generic_adapter import GenericAdapter
from sahiixx_agency.core.memory import AgencyMemory
from sahiixx_agency.core.models import RepoCategory, RepoNode
from sahiixx_agency.core.security import AuditLogger, NetworkPolicy


@pytest.mark.asyncio
async def test_generic_adapter_runs_inferred_command(tmp_path, monkeypatch):
    repo = tmp_path / "demo"
    repo.mkdir()
    (repo / "main.py").write_text("print('hello from demo')")

    node = RepoNode(
        id="demo",
        name="demo",
        owner="test",
        full_name="test/demo",
        url="https://github.com/test/demo",
        category=RepoCategory.UNCATEGORIZED,
    )

    captured: dict[str, Any] = {}

    def fake_run(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = "hello from demo"
        mock.stderr = ""
        return mock

    monkeypatch.setattr("sahiixx_agency.adapters.generic_adapter.subprocess.run", fake_run)

    adapter = GenericAdapter(data_dir=str(tmp_path))
    result = await adapter.run(node, {"command": "python main.py"})
    assert result["status"] == "success"
    assert result["returncode"] == 0
    assert captured["args"] == (["python", "main.py"],)


@pytest.mark.asyncio
async def test_generic_adapter_runs_sequential_entrypoint_steps(tmp_path, monkeypatch):
    repo = tmp_path / "demo"
    repo.mkdir()
    (repo / "package.json").write_text('{"scripts": {"dev": "next dev"}}')

    node = RepoNode(
        id="demo",
        name="demo",
        owner="test",
        full_name="test/demo",
        url="https://github.com/test/demo",
        category=RepoCategory.UNCATEGORIZED,
    )

    commands: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        commands.append(cmd)
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = ""
        mock.stderr = ""
        return mock

    monkeypatch.setattr("sahiixx_agency.adapters.generic_adapter.subprocess.run", fake_run)

    adapter = GenericAdapter(data_dir=str(tmp_path))
    result = await adapter.run(node, {})
    assert result["status"] == "success"
    assert commands == [["npm", "install"], ["npm", "run", "dev"]]


@pytest.mark.asyncio
async def test_generic_adapter_stops_on_failed_step(tmp_path, monkeypatch):
    repo = tmp_path / "demo"
    repo.mkdir()
    (repo / "package.json").write_text('{"scripts": {"dev": "next dev"}}')

    node = RepoNode(
        id="demo",
        name="demo",
        owner="test",
        full_name="test/demo",
        url="https://github.com/test/demo",
        category=RepoCategory.UNCATEGORIZED,
    )

    commands: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        commands.append(cmd)
        mock = MagicMock()
        mock.returncode = 1 if cmd == ["npm", "install"] else 0
        mock.stdout = ""
        mock.stderr = "install failed"
        return mock

    monkeypatch.setattr("sahiixx_agency.adapters.generic_adapter.subprocess.run", fake_run)

    adapter = GenericAdapter(data_dir=str(tmp_path), fallback_on_failure=False)
    result = await adapter.run(node, {})
    assert result["status"] == "error"
    assert commands == [["npm", "install"]]


@pytest.mark.asyncio
async def test_generic_adapter_simulates_when_no_local_clone():
    node = RepoNode(
        id="missing",
        name="missing",
        owner="test",
        full_name="test/missing",
        url="https://github.com/test/missing",
    )
    adapter = GenericAdapter(data_dir="/nonexistent")
    result = await adapter.run(node, {})
    assert result["status"] == "simulated"


@pytest.mark.asyncio
async def test_generic_adapter_blocks_host_outside_allowlist(tmp_path):
    """GenericAdapter should enforce the supplied network policy before running."""
    repo = tmp_path / "demo"
    repo.mkdir()
    (repo / "main.py").write_text("print('hello')")

    node = RepoNode(
        id="demo",
        name="demo",
        owner="test",
        full_name="test/demo",
        url="https://github.com/test/demo",
        external_hosts=["evil.com"],
    )

    policy = NetworkPolicy(allowlist=["github.com"], default_allow=False)
    adapter = GenericAdapter(data_dir=str(tmp_path), network_policy=policy)

    with pytest.raises(RuntimeError, match="Network policy blocks"):
        await adapter.run(node, {"command": "python main.py"})


@pytest.mark.asyncio
async def test_generic_adapter_allows_host_in_allowlist(tmp_path, monkeypatch):
    """GenericAdapter should proceed when declared hosts are in the allowlist."""
    repo = tmp_path / "demo"
    repo.mkdir()
    (repo / "main.py").write_text("print('hello')")

    node = RepoNode(
        id="demo",
        name="demo",
        owner="test",
        full_name="test/demo",
        url="https://github.com/test/demo",
        external_hosts=["api.github.com"],
    )

    def fake_run(cmd, **kwargs):
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = "hello"
        mock.stderr = ""
        return mock

    monkeypatch.setattr("sahiixx_agency.adapters.generic_adapter.subprocess.run", fake_run)

    policy = NetworkPolicy(allowlist=["github.com"], default_allow=False)
    adapter = GenericAdapter(data_dir=str(tmp_path), network_policy=policy)
    result = await adapter.run(node, {"command": "python main.py"})
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_generic_adapter_blocked_host_logs_audit(tmp_path):
    """A blocked host writes an audit event when an audit logger is wired."""
    repo = tmp_path / "demo"
    repo.mkdir()
    (repo / "main.py").write_text("print('hello')")

    node = RepoNode(
        id="demo",
        name="demo",
        owner="test",
        full_name="test/demo",
        url="https://github.com/test/demo",
        external_hosts=["evil.com"],
    )

    memory = AgencyMemory(data_dir=str(tmp_path), backend="json")
    audit = AuditLogger(memory)
    policy = NetworkPolicy(allowlist=["github.com"], default_allow=False)
    adapter = GenericAdapter(data_dir=str(tmp_path), network_policy=policy, audit_logger=audit)

    with pytest.raises(RuntimeError):
        await adapter.run(node, {"command": "python main.py"})

    events = memory.recent_events(topic="audit")
    assert len(events) == 1
    assert events[0]["payload"]["action"] == "network_policy_violation"
    assert "evil.com" in events[0]["payload"]["details"]["blocked_hosts"]
