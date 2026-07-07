"""Tests for the dependency vulnerability scanner."""

from __future__ import annotations

import asyncio
import json
import subprocess

import pytest

from sahiixx_agency.core.dependency_scanner import DependencyScanner
from sahiixx_agency.core.engine import AgencyEngine
from sahiixx_agency.core.models import AgencyConfig, AgencyTask, RepoCategory, RepoNode, TaskStatus


@pytest.fixture
def scanner(tmp_path):
    return DependencyScanner(data_dir=str(tmp_path))


@pytest.mark.asyncio
async def test_python_scan_passes_when_no_vulnerable_deps(tmp_path, scanner):
    repo_dir = tmp_path / "repos" / "safe-py"
    repo_dir.mkdir(parents=True)
    (repo_dir / "requirements.txt").write_text("requests==2.32.0\nflask>=2.0\n")
    node = RepoNode(
        id="safe-py",
        name="safe-py",
        full_name="sahiixx/safe-py",
        url="https://github.com/sahiixx/safe-py",
        language="python",
    )
    report = await scanner.scan(node)
    assert report.passed is True
    assert report.failures == []


@pytest.mark.asyncio
async def test_python_scan_fails_on_requests_2_6_0(tmp_path, scanner):
    repo_dir = tmp_path / "repos" / "bad-py"
    repo_dir.mkdir(parents=True)
    (repo_dir / "requirements.txt").write_text("requests==2.6.0\n")
    node = RepoNode(
        id="bad-py",
        name="bad-py",
        full_name="sahiixx/bad-py",
        url="https://github.com/sahiixx/bad-py",
        language="python",
    )
    report = await scanner.scan(node)
    assert report.passed is False
    assert any("CVE-2015-2296" in f for f in report.failures)
    assert any("requests" in f and "2.6.0" in f for f in report.failures)


@pytest.mark.asyncio
async def test_python_scan_falls_back_to_pyproject(tmp_path, scanner):
    repo_dir = tmp_path / "repos" / "pyproject-bad"
    repo_dir.mkdir(parents=True)
    (repo_dir / "pyproject.toml").write_text(
        '[project]\nname = "demo"\ndependencies = ["requests==2.6.0"]\n'
    )
    node = RepoNode(
        id="pyproject-bad",
        name="pyproject-bad",
        full_name="sahiixx/pyproject-bad",
        url="https://github.com/sahiixx/pyproject-bad",
        language="python",
    )
    report = await scanner.scan(node)
    assert report.passed is False
    assert any("requests" in f and "2.6.0" in f for f in report.failures)


@pytest.mark.asyncio
async def test_node_scan_fails_on_lodash(tmp_path, scanner):
    repo_dir = tmp_path / "repos" / "bad-node"
    repo_dir.mkdir(parents=True)
    (repo_dir / "package.json").write_text(
        '{"name": "bad-node", "dependencies": {"lodash": "4.17.20"}}'
    )
    node = RepoNode(
        id="bad-node",
        name="bad-node",
        full_name="sahiixx/bad-node",
        url="https://github.com/sahiixx/bad-node",
        language="javascript",
    )
    report = await scanner.scan(node)
    assert report.passed is False
    assert any("CVE-2021-23337" in f for f in report.failures)
    assert any("lodash < 4.17.21" in f for f in report.failures)


@pytest.mark.asyncio
async def test_node_scan_passes_on_safe_lodash(tmp_path, scanner):
    repo_dir = tmp_path / "repos" / "safe-node"
    repo_dir.mkdir(parents=True)
    (repo_dir / "package.json").write_text(
        '{"name": "safe-node", "dependencies": {"lodash": "4.17.21"}}'
    )
    node = RepoNode(
        id="safe-node",
        name="safe-node",
        full_name="sahiixx/safe-node",
        url="https://github.com/sahiixx/safe-node",
        language="javascript",
    )
    report = await scanner.scan(node)
    assert report.passed is True
    assert report.failures == []


@pytest.mark.asyncio
async def test_unsupported_language_passes(tmp_path, scanner):
    repo_dir = tmp_path / "repos" / "rust-repo"
    repo_dir.mkdir(parents=True)
    node = RepoNode(
        id="rust-repo",
        name="rust-repo",
        full_name="sahiixx/rust-repo",
        url="https://github.com/sahiixx/rust-repo",
        language="rust",
    )
    report = await scanner.scan(node)
    assert report.passed is True
    assert "Unsupported language" in (report.stderr or "")


@pytest.mark.asyncio
async def test_missing_repo_passes(tmp_path, scanner):
    node = RepoNode(
        id="missing-repo",
        name="missing-repo",
        full_name="sahiixx/missing-repo",
        url="https://github.com/sahiixx/missing-repo",
        language="python",
    )
    report = await scanner.scan(node)
    assert report.passed is True
    assert "Repo not cloned" in (report.stderr or "")


@pytest.mark.asyncio
async def test_engine_blocks_execution_on_failed_scan(tmp_path, monkeypatch):
    config = AgencyConfig(
        data_dir=str(tmp_path),
        security={"dependency_scan_enabled": True},
    )
    engine = AgencyEngine(config)

    repo_dir = tmp_path / "repos" / "bad-py"
    repo_dir.mkdir(parents=True)
    (repo_dir / "requirements.txt").write_text("requests==2.6.0\n")
    mod = RepoNode(
        id="bad-py",
        name="bad-py",
        full_name="sahiixx/bad-py",
        url="https://github.com/sahiixx/bad-py",
        language="python",
    )
    engine.registry._modules["bad-py"] = mod

    run_called = False

    async def fake_run(self, node, payload):
        nonlocal run_called
        run_called = True
        return {"status": "success"}

    monkeypatch.setattr(
        "sahiixx_agency.adapters.generic_adapter.GenericAdapter.run",
        fake_run,
    )

    task = AgencyTask(id="t1", intent="run bad-py", module_id="bad-py")
    await engine._execute_task(task)

    assert task.status == TaskStatus.FAILED
    assert task.error == "Dependency vulnerability scan failed"
    assert task.result is not None
    scan_report = task.result.get("dependency_scan", {})
    assert scan_report.get("passed") is False
    assert any("CVE-2015-2296" in f for f in scan_report.get("failures", []))
    assert run_called is False


@pytest.mark.asyncio
async def test_engine_allows_execution_when_scan_passes(tmp_path, monkeypatch):
    config = AgencyConfig(
        data_dir=str(tmp_path),
        security={"dependency_scan_enabled": True},
    )
    engine = AgencyEngine(config)

    repo_dir = tmp_path / "repos" / "safe-py"
    repo_dir.mkdir(parents=True)
    (repo_dir / "requirements.txt").write_text("requests==2.32.0\n")
    mod = RepoNode(
        id="safe-py",
        name="safe-py",
        full_name="sahiixx/safe-py",
        url="https://github.com/sahiixx/safe-py",
        language="python",
    )
    engine.registry._modules["safe-py"] = mod

    async def fake_run(self, node, payload):
        return {"status": "success", "module": node.name}

    monkeypatch.setattr(
        "sahiixx_agency.adapters.generic_adapter.GenericAdapter.run",
        fake_run,
    )

    task = AgencyTask(id="t2", intent="run safe-py", module_id="safe-py")
    await engine._execute_task(task)

    assert task.status == TaskStatus.COMPLETED
    assert task.result is not None
    assert task.result.get("execution", {}).get("status") == "success"


@pytest.mark.asyncio
async def test_engine_skips_scan_when_disabled(tmp_path, monkeypatch):
    config = AgencyConfig(
        data_dir=str(tmp_path),
        security={"dependency_scan_enabled": False},
    )
    engine = AgencyEngine(config)

    repo_dir = tmp_path / "repos" / "bad-py"
    repo_dir.mkdir(parents=True)
    (repo_dir / "requirements.txt").write_text("requests==2.6.0\n")
    mod = RepoNode(
        id="bad-py",
        name="bad-py",
        full_name="sahiixx/bad-py",
        url="https://github.com/sahiixx/bad-py",
        language="python",
    )
    engine.registry._modules["bad-py"] = mod

    async def fake_run(self, node, payload):
        return {"status": "success", "module": node.name}

    monkeypatch.setattr(
        "sahiixx_agency.adapters.generic_adapter.GenericAdapter.run",
        fake_run,
    )

    task = AgencyTask(id="t3", intent="run bad-py", module_id="bad-py")
    await engine._execute_task(task)

    assert task.status == TaskStatus.COMPLETED
    assert "dependency_scan" not in (task.result or {})


@pytest.mark.asyncio
async def test_nonzero_cli_exit_with_no_parseable_findings_fails_closed(tmp_path, scanner, monkeypatch):
    """A non-zero CLI exit with no parseable findings must fail closed."""
    repo_dir = tmp_path / "repos" / "npm-no-findings"
    repo_dir.mkdir(parents=True)
    (repo_dir / "package.json").write_text('{"name": "npm-no-findings", "dependencies": {}}')
    node = RepoNode(
        id="npm-no-findings",
        name="npm-no-findings",
        full_name="sahiixx/npm-no-findings",
        url="https://github.com/sahiixx/npm-no-findings",
        language="javascript",
    )

    def fake_run(cmd, **kwargs):
        class Result:
            returncode = 1
            stdout = ""
            stderr = "npm ERR! missing lockfile"
        return Result()

    monkeypatch.setattr("sahiixx_agency.core.dependency_scanner.subprocess.run", fake_run)

    report = await scanner.scan(node)
    assert report.passed is False
    assert any("missing lockfile" in f for f in report.failures)


@pytest.mark.asyncio
async def test_engine_blocks_specialized_adapter_on_failed_scan(tmp_path, monkeypatch):
    """The dependency scan gate must block specialized adapters, not only generic fallback."""
    config = AgencyConfig(
        data_dir=str(tmp_path),
        security={"dependency_scan_enabled": True},
    )
    engine = AgencyEngine(config)

    repo_dir = tmp_path / "repos" / "career-ops"
    repo_dir.mkdir(parents=True)
    (repo_dir / "requirements.txt").write_text("requests==2.6.0\n")
    mod = RepoNode(
        id="career-ops",
        name="career-ops",
        full_name="sahiixx/career-ops",
        url="https://github.com/sahiixx/career-ops",
        language="python",
    )
    engine.registry._modules["career-ops"] = mod

    run_called = False

    async def fake_run(self, node, payload):
        nonlocal run_called
        run_called = True
        return {"status": "success"}

    monkeypatch.setattr(
        "sahiixx_agency.adapters.career.career_ops_adapter.CareerOpsAdapter.run",
        fake_run,
    )

    task = AgencyTask(id="t-career", intent="run career-ops", module_id="career-ops")
    await engine._execute_task(task)

    assert task.status == TaskStatus.FAILED
    assert task.error == "Dependency vulnerability scan failed"
    assert task.result is not None
    scan_report = task.result.get("dependency_scan", {})
    assert scan_report.get("passed") is False
    assert run_called is False


@pytest.mark.asyncio
async def test_scan_is_awaitable(tmp_path, scanner):
    """DependencyScanner.scan is async and returns an awaitable."""
    repo_dir = tmp_path / "repos" / "async-py"
    repo_dir.mkdir(parents=True)
    (repo_dir / "requirements.txt").write_text("requests==2.32.0\n")
    node = RepoNode(
        id="async-py",
        name="async-py",
        full_name="sahiixx/async-py",
        url="https://github.com/sahiixx/async-py",
        language="python",
    )
    coro = scanner.scan(node)
    assert asyncio.iscoroutine(coro)
    report = await coro
    assert report.passed is True


@pytest.mark.asyncio
async def test_timeout_triggers_static_fallback(tmp_path, scanner, monkeypatch):
    """A CLI timeout must not fail open; static fallback should still run."""
    repo_dir = tmp_path / "repos" / "timeout-py"
    repo_dir.mkdir(parents=True)
    (repo_dir / "requirements.txt").write_text("requests==2.6.0\n")
    node = RepoNode(
        id="timeout-py",
        name="timeout-py",
        full_name="sahiixx/timeout-py",
        url="https://github.com/sahiixx/timeout-py",
        language="python",
    )

    def raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["pip-audit"], timeout=120)

    monkeypatch.setattr("sahiixx_agency.core.dependency_scanner.subprocess.run", raise_timeout)

    report = await scanner.scan(node)
    assert report.passed is False
    assert any("CVE-2015-2296" in f for f in report.failures)
    assert "pip-audit --requirement" in (report.command or "")


@pytest.mark.asyncio
async def test_npm_audit_nonzero_parses_real_findings(tmp_path, scanner, monkeypatch):
    """Non-zero npm audit exit must parse JSON vulnerabilities, not drop them."""
    repo_dir = tmp_path / "repos" / "npm-vuln"
    repo_dir.mkdir(parents=True)
    (repo_dir / "package.json").write_text('{"name": "npm-vuln", "dependencies": {}}')
    node = RepoNode(
        id="npm-vuln",
        name="npm-vuln",
        full_name="sahiixx/npm-vuln",
        url="https://github.com/sahiixx/npm-vuln",
        language="javascript",
    )

    fake_stdout = json.dumps({
        "vulnerabilities": {
            "lodash": {
                "name": "lodash",
                "severity": "high",
                "via": [{"title": "Prototype Pollution", "cwe": ["CWE-400"]}],
                "range": "<4.17.21",
            }
        }
    })

    def fake_run(cmd, **kwargs):
        class Result:
            returncode = 1
            stdout = fake_stdout
            stderr = ""
        return Result()

    monkeypatch.setattr("sahiixx_agency.core.dependency_scanner.subprocess.run", fake_run)

    report = await scanner.scan(node)
    assert report.passed is False
    assert any("lodash" in f and "high" in f for f in report.failures)
    assert any("Prototype Pollution" in f for f in report.failures)


@pytest.mark.asyncio
async def test_pip_audit_local_for_pyproject_only(tmp_path, scanner, monkeypatch):
    """pyproject-only repos should attempt ``pip-audit --local``."""
    repo_dir = tmp_path / "repos" / "pyproject-only"
    repo_dir.mkdir(parents=True)
    (repo_dir / "pyproject.toml").write_text(
        '[project]\nname = "demo"\ndependencies = ["requests==2.32.0"]\n'
    )
    node = RepoNode(
        id="pyproject-only",
        name="pyproject-only",
        full_name="sahiixx/pyproject-only",
        url="https://github.com/sahiixx/pyproject-only",
        language="python",
    )

    commands_run: list[list[str]] = []

    def capture_run(cmd, **kwargs):
        commands_run.append(cmd)
        raise FileNotFoundError(cmd[0])

    monkeypatch.setattr("sahiixx_agency.core.dependency_scanner.subprocess.run", capture_run)

    report = await scanner.scan(node)
    assert report.passed is True
    assert any("--local" in " ".join(c) for c in commands_run)


@pytest.mark.asyncio
async def test_pip_audit_nonzero_parses_real_findings(tmp_path, scanner, monkeypatch):
    """Non-zero pip-audit exit must parse package names from text output."""
    repo_dir = tmp_path / "repos" / "pip-vuln"
    repo_dir.mkdir(parents=True)
    (repo_dir / "requirements.txt").write_text("requests==2.6.0\n")
    node = RepoNode(
        id="pip-vuln",
        name="pip-vuln",
        full_name="sahiixx/pip-vuln",
        url="https://github.com/sahiixx/pip-vuln",
        language="python",
    )

    fake_stdout = "Found 1 known vulnerabilities in 1 package\nrequests  2.6.0   PYSEC-2015-2296   2.32.0"

    def fake_run(cmd, **kwargs):
        class Result:
            returncode = 1
            stdout = fake_stdout
            stderr = ""
        return Result()

    monkeypatch.setattr("sahiixx_agency.core.dependency_scanner.subprocess.run", fake_run)

    report = await scanner.scan(node)
    assert report.passed is False
    assert any("requests" in f for f in report.failures)


@pytest.mark.asyncio
async def test_version_parser_handles_caret_and_prerelease(tmp_path, scanner):
    """Version parser should strip npm caret ranges and pre-release suffixes."""
    repo_dir = tmp_path / "repos" / "caret-node"
    repo_dir.mkdir(parents=True)
    (repo_dir / "package.json").write_text(
        '{"name": "caret-node", "dependencies": {"lodash": "^4.17.20"}}'
    )
    node = RepoNode(
        id="caret-node",
        name="caret-node",
        full_name="sahiixx/caret-node",
        url="https://github.com/sahiixx/caret-node",
        language="javascript",
    )
    report = await scanner.scan(node)
    assert report.passed is False
    assert any("CVE-2021-23337" in f for f in report.failures)


@pytest.mark.asyncio
async def test_version_parser_handles_compatible_release(tmp_path, scanner):
    """Compatible-release operator ~= should be parsed and matched."""
    repo_dir = tmp_path / "repos" / "compat-py"
    repo_dir.mkdir(parents=True)
    (repo_dir / "requirements.txt").write_text("requests~=2.6.0\n")
    node = RepoNode(
        id="compat-py",
        name="compat-py",
        full_name="sahiixx/compat-py",
        url="https://github.com/sahiixx/compat-py",
        language="python",
    )
    report = await scanner.scan(node)
    assert report.passed is False
    assert any("requests" in f and "2.6.0" in f for f in report.failures)


@pytest.mark.asyncio
async def test_engine_blocks_category_adapter_on_failed_scan(tmp_path, monkeypatch):
    """The dependency scan gate must block category-adapter execution paths."""
    config = AgencyConfig(
        data_dir=str(tmp_path),
        security={"dependency_scan_enabled": True},
    )
    engine = AgencyEngine(config)

    repo_dir = tmp_path / "repos" / "career-cat"
    repo_dir.mkdir(parents=True)
    (repo_dir / "requirements.txt").write_text("requests==2.6.0\n")
    mod = RepoNode(
        id="career-cat",
        name="career-cat",
        full_name="sahiixx/career-cat",
        url="https://github.com/sahiixx/career-cat",
        language="python",
        category=RepoCategory.CAREER,
        stars=10,
    )
    engine.registry._modules["career-cat"] = mod

    run_called = False

    async def fake_run(self, node, payload):
        nonlocal run_called
        run_called = True
        return {"status": "success"}

    monkeypatch.setattr(
        "sahiixx_agency.core.runner.RepoRunner.run",
        fake_run,
    )

    task = AgencyTask(
        id="t-career-cat",
        intent="find jobs",
        category=RepoCategory.CAREER,
    )
    await engine._execute_task(task)

    assert task.status == TaskStatus.FAILED
    assert task.error == "Dependency vulnerability scan failed"
    assert task.result is not None
    scan_report = task.result.get("dependency_scan", {})
    assert scan_report.get("passed") is False
    assert any("CVE-2015-2296" in f for f in scan_report.get("failures", []))
    assert run_called is False
