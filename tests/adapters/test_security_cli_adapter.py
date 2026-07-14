from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from sahiixx_agency.adapters.security.security_cli_adapter import (
    SecurityCliAdapter,
    SecurityCliResult,
)
from sahiixx_agency.core.models import RepoNode
from sahiixx_agency.core.security import NetworkPolicy


def _node() -> RepoNode:
    return RepoNode(
        id="trufflehog",
        name="trufflehog",
        owner="trufflesecurity",
        full_name="trufflesecurity/trufflehog",
        url="https://github.com/trufflesecurity/trufflehog",
    )


def test_empty_brief_fails():
    adapter = SecurityCliAdapter(binary="trufflehog", default_args=["filesystem", "."])
    result = adapter.dispatch("")
    assert isinstance(result, SecurityCliResult)
    assert result.ok is False
    assert result.status == "failed"


def test_simulate_when_binary_absent(monkeypatch):
    monkeypatch.setattr(
        "sahiixx_agency.adapters.security.security_cli_adapter.shutil.which",
        lambda _: None,
    )
    adapter = SecurityCliAdapter(binary="trufflehog", default_args=["filesystem", "."])
    result = adapter.dispatch("scan repo for secrets")
    assert result.status == "simulated"
    assert result.ok is True
    assert "trufflehog" in result.command
    assert result.metadata.get("fallback") is True


def test_shannon_simulates_when_binary_absent(monkeypatch):
    monkeypatch.setattr(
        "sahiixx_agency.adapters.security.security_cli_adapter.shutil.which",
        lambda _: None,
    )
    adapter = SecurityCliAdapter(binary="shannon", default_args=[])
    result = adapter.dispatch("pentest example.com")
    assert result.status == "simulated"


def test_fallback_on_subprocess_failure(monkeypatch):
    monkeypatch.setattr(
        "sahiixx_agency.adapters.security.security_cli_adapter.shutil.which",
        lambda _: "/usr/bin/trufflehog",
    )

    def fake_run(cmd, **kwargs):
        mock = MagicMock()
        mock.returncode = 1
        mock.stdout = ""
        mock.stderr = "trufflehog: command error"
        return mock

    monkeypatch.setattr(
        "sahiixx_agency.adapters.security.security_cli_adapter.subprocess.run",
        fake_run,
    )
    adapter = SecurityCliAdapter(
        binary="trufflehog", default_args=["filesystem", "."], fallback_on_failure=True
    )
    result = adapter.dispatch("scan repo")
    assert result.status == "simulated"
    assert result.metadata.get("original_error") == "trufflehog: command error"


def test_no_fallback_on_subprocess_failure(monkeypatch):
    monkeypatch.setattr(
        "sahiixx_agency.adapters.security.security_cli_adapter.shutil.which",
        lambda _: "/usr/bin/trufflehog",
    )

    def fake_run(cmd, **kwargs):
        mock = MagicMock()
        mock.returncode = 1
        mock.stdout = ""
        mock.stderr = "boom"
        return mock

    monkeypatch.setattr(
        "sahiixx_agency.adapters.security.security_cli_adapter.subprocess.run",
        fake_run,
    )
    adapter = SecurityCliAdapter(
        binary="trufflehog",
        default_args=["filesystem", "."],
        fallback_on_failure=False,
    )
    result = adapter.dispatch("scan repo")
    assert result.ok is False
    assert result.status == "error"


@pytest.mark.asyncio
async def test_network_policy_blocks():
    adapter = SecurityCliAdapter(binary="trufflehog", default_args=["filesystem", "."])
    adapter.network_policy = NetworkPolicy(
        allowlist=["github.com"], default_allow=False
    )
    node = _node()
    node.external_hosts = ["evil.com"]
    with pytest.raises(RuntimeError, match="Network policy blocks"):
        await adapter.run(node, {"brief": "scan", "simulate": False})


@pytest.mark.asyncio
async def test_async_run_simulate(monkeypatch):
    monkeypatch.setattr(
        "sahiixx_agency.adapters.security.security_cli_adapter.shutil.which",
        lambda _: None,
    )
    adapter = SecurityCliAdapter(binary="trufflehog", default_args=["filesystem", "."])
    result = await adapter.run(_node(), {"brief": "scan repo", "simulate": True})
    assert result["status"] == "simulated"
    assert result["command"].endswith("<simulated>")
