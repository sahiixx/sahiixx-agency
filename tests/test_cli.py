"""Tests for the Typer CLI."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from sahiixx_agency.cli.main import app

runner = CliRunner()


@pytest.fixture
def patched_engine(monkeypatch, tmp_path):
    from sahiixx_agency.core.engine import AgencyEngine
    from sahiixx_agency.core.models import AgencyConfig, RepoCategory, RepoNode

    config = AgencyConfig(data_dir=str(tmp_path))
    engine = AgencyEngine(config)

    fake_modules = [
        RepoNode(
            id="friday",
            name="friday",
            full_name="sahiixx/friday",
            url="https://github.com/sahiixx/friday",
            category=RepoCategory.VOICE_AI,
            language="python",
            stars=50,
            capabilities=["voice"],
        ),
    ]
    for module in fake_modules:
        engine.registry._modules[module.id] = module

    async def fake_discover(username: str) -> list[RepoNode]:
        for module in fake_modules:
            engine.registry._modules[module.id] = module
        return fake_modules

    monkeypatch.setattr(engine.registry, "discover", fake_discover)
    monkeypatch.setattr(
        engine.runner,
        "run",
        lambda module, command="run", env=None, timeout=60: {
            "module": module.name,
            "status": "success",
            "returncode": 0,
            "stdout": "ok",
            "stderr": "",
            "command": command,
        },
    )

    monkeypatch.setattr("sahiixx_agency.cli.main.AgencyEngine", lambda config=None: engine)
    return engine


def test_dispatch_command_returns_task_id(patched_engine):
    result = runner.invoke(app, ["dispatch", "run voice assistant", "--no-wait"])
    assert result.exit_code == 0
    assert "task_" in result.stdout
    assert "pending" in result.stdout


def test_task_status_unknown_id(patched_engine):
    result = runner.invoke(app, ["task", "status", "task_does_not_exist"])
    assert result.exit_code == 1
    assert "not found" in result.stdout.lower()


def test_exec_invalid_json_payload(patched_engine):
    result = runner.invoke(app, ["exec", "friday", "--payload", "not-json"])
    assert result.exit_code == 1
    assert "invalid json" in result.stdout.lower()
