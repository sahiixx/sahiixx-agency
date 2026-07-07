"""Tests for the generic repo runner."""

from __future__ import annotations

from pathlib import Path

import pytest

from sahiixx_agency.core.memory import AgencyMemory
from sahiixx_agency.core.models import RepoNode
from sahiixx_agency.core.runner import RepoRunner
from sahiixx_agency.core.security import AuditLogger, NetworkPolicy


class FakeCloneManager:
    """CloneManager stand-in that returns a pre-existing local path."""

    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path

    async def clone(self, node: RepoNode) -> Path:  # noqa: ARG002
        return self.repo_path


@pytest.fixture
def runnable_repo(tmp_path: Path) -> Path:
    """Create a local Python repo and return its path."""
    repo_path = tmp_path / "test-repo"
    repo_path.mkdir()
    (repo_path / "main.py").write_text('print("hello from runner")', encoding="utf-8")
    return repo_path


@pytest.fixture
def runnable_node(runnable_repo: Path) -> RepoNode:
    return RepoNode(
        id="test-repo",
        name="test-repo",
        owner="tester",
        full_name="tester/test-repo",
        url="https://github.com/tester/test-repo",
        local_path=str(runnable_repo),
    )


@pytest.fixture
def runner(runnable_repo: Path) -> RepoRunner:
    return RepoRunner(FakeCloneManager(runnable_repo))


@pytest.mark.asyncio
async def test_runner_executes_runnable_repo(runner: RepoRunner, runnable_node: RepoNode) -> None:
    result = await runner.run(runnable_node)
    assert result["status"] == "success"
    assert result["returncode"] == 0
    assert "hello from runner" in result["stdout"]


@pytest.mark.asyncio
async def test_runner_default_allow_no_policy(runner: RepoRunner, runnable_node: RepoNode) -> None:
    """When no policy is supplied, external hosts are not checked."""
    runnable_node.external_hosts = ["evil.com"]
    result = await runner.run(runnable_node)
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_runner_allow_all_policy_allows_hosts(
    runner: RepoRunner, runnable_node: RepoNode
) -> None:
    """Default NetworkPolicy allows all hosts, so execution proceeds."""
    runnable_node.external_hosts = ["evil.com"]
    runner.network_policy = NetworkPolicy()
    result = await runner.run(runnable_node)
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_runner_blocked_host_raises(runner: RepoRunner, runnable_node: RepoNode) -> None:
    """A declared host outside the allowlist blocks execution."""
    runner.network_policy = NetworkPolicy(allowlist=["github.com"], default_allow=False)
    runnable_node.external_hosts = ["evil.com", "api.github.com"]
    with pytest.raises(RuntimeError, match="Network policy blocks"):
        await runner.run(runnable_node)


@pytest.mark.asyncio
async def test_runner_allowed_host_passes(runner: RepoRunner, runnable_node: RepoNode) -> None:
    """A declared host matching the allowlist is permitted."""
    runner.network_policy = NetworkPolicy(allowlist=["github.com"], default_allow=False)
    runnable_node.external_hosts = ["api.github.com"]
    result = await runner.run(runnable_node)
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_runner_allowed_host_subdomain(
    runner: RepoRunner, runnable_node: RepoNode
) -> None:
    """Subdomain matching works for the allowlist."""
    runner.network_policy = NetworkPolicy(allowlist=["openai.com"], default_allow=False)
    runnable_node.external_hosts = ["api.openai.com"]
    result = await runner.run(runnable_node)
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_runner_blocked_host_logs_audit(
    runner: RepoRunner, runnable_node: RepoNode, tmp_path: Path
) -> None:
    """A blocked host writes an audit event when an audit logger is wired."""
    memory = AgencyMemory(data_dir=str(tmp_path), backend="json")
    runner.audit_logger = AuditLogger(memory)
    runner.network_policy = NetworkPolicy(allowlist=["github.com"], default_allow=False)
    runnable_node.external_hosts = ["evil.com"]

    with pytest.raises(RuntimeError):
        await runner.run(runnable_node)

    events = memory.recent_events(topic="audit")
    assert len(events) == 1
    payload = events[0]["payload"]
    assert payload["action"] == "network_policy_violation"
    assert "evil.com" in payload["details"]["blocked_hosts"]


@pytest.mark.asyncio
async def test_runner_network_policy_run_override(
    runner: RepoRunner, runnable_node: RepoNode
) -> None:
    """A policy passed directly to run() overrides the runner-level policy."""
    runner.network_policy = NetworkPolicy(allowlist=["github.com"], default_allow=False)
    runnable_node.external_hosts = ["evil.com"]
    permissive = NetworkPolicy()
    result = await runner.run(runnable_node, network_policy=permissive)
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_runner_no_external_hosts_with_restrictive_policy(
    runner: RepoRunner, runnable_node: RepoNode
) -> None:
    """A restrictive policy does not block repos that declare no external hosts."""
    runner.network_policy = NetworkPolicy(allowlist=["github.com"], default_allow=False)
    runnable_node.external_hosts = []
    result = await runner.run(runnable_node)
    assert result["status"] == "success"


def test_network_policy_allow_all_property() -> None:
    assert NetworkPolicy().allow_all is True
    assert NetworkPolicy(allowlist=["github.com"]).allow_all is False
    assert NetworkPolicy(blocklist=["evil.com"]).allow_all is False
    assert NetworkPolicy(default_allow=False).allow_all is False
