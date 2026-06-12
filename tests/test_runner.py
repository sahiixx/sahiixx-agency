"""Tests for the repo runner and dependency installation."""

import asyncio
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from sahiixx_agency.core.models import RepoCategory, RepoNode
from sahiixx_agency.core.runner import CloneManager, RepoRunner


def _fake_node(name: str = "demo") -> RepoNode:
    return RepoNode(
        id=name,
        name=name,
        full_name=f"sahiixx/{name}",
        description="A demo repo",
        url=f"https://github.com/sahiixx/{name}",
        category=RepoCategory.AGENT_FRAMEWORK,
        language="Python",
    )


def _stub_repo(path: Path, has_requirements: bool = False, has_pyproject: bool = False) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "main.py").write_text("print('hello')\n")
    if has_requirements:
        (path / "requirements.txt").write_text("requests\n")
    if has_pyproject:
        (path / "pyproject.toml").write_text(
            '[build-system]\nrequires = ["hatchling"]\n' '[project]\nname = "demo"\nversion = "0.1.0"\n'
        )


def _create_fake_venv(runner: RepoRunner, repo_path: Path) -> None:
    """Create the venv python stub so the runner uses it for execution."""
    venv_python = runner._venv_python(repo_path)
    venv_python.parent.mkdir(parents=True, exist_ok=True)
    venv_python.touch()


def test_runner_installs_python_requirements(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_path = tmp_path / "demo"
    _stub_repo(repo_path, has_requirements=True)

    runner = RepoRunner(CloneManager())
    _create_fake_venv(runner, repo_path)
    monkeypatch.setattr(runner.clone_manager, "clone", AsyncMock(return_value=repo_path))

    commands: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = asyncio.run(runner.run(_fake_node()))

    assert result["status"] == "success"
    assert any("requirements.txt" in str(c) for c in commands)
    assert str(runner._venv_python(repo_path)) in result["command"]


def test_runner_installs_pyproject_dependencies(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_path = tmp_path / "demo"
    _stub_repo(repo_path, has_pyproject=True)

    runner = RepoRunner(CloneManager())
    _create_fake_venv(runner, repo_path)
    monkeypatch.setattr(runner.clone_manager, "clone", AsyncMock(return_value=repo_path))

    commands: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = asyncio.run(runner.run(_fake_node()))

    assert result["status"] == "success"
    assert any("-e" in str(c) and "." in str(c) for c in commands)


def test_runner_skips_install_when_requested(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_path = tmp_path / "demo"
    _stub_repo(repo_path, has_requirements=True)

    runner = RepoRunner(CloneManager())
    monkeypatch.setattr(runner.clone_manager, "clone", AsyncMock(return_value=repo_path))

    commands: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = asyncio.run(runner.run(_fake_node(), skip_install=True))

    assert result["status"] == "success"
    assert not any("requirements.txt" in str(c) for c in commands)
    assert not any("-m" in c and "venv" in c for c in commands)
