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


def test_do_command_natural_language_dispatch(patched_engine):
    result = runner.invoke(app, ["do", "run", "voice", "assistant", "--no-wait"])
    assert result.exit_code == 0
    assert "task_" in result.stdout
    assert "pending" in result.stdout


def test_do_command_invalid_json_payload(patched_engine):
    result = runner.invoke(app, ["do", "run", "voice", "assistant", "--payload", "not-json"])
    assert result.exit_code == 1
    assert "invalid json" in result.stdout.lower()


def test_task_status_unknown_id(patched_engine):
    result = runner.invoke(app, ["task", "status", "task_does_not_exist"])
    assert result.exit_code == 1
    assert "not found" in result.stdout.lower()


def test_task_list_shows_dispatched_tasks(patched_engine):
    runner.invoke(app, ["do", "run", "voice", "assistant", "--no-wait"])
    result = runner.invoke(app, ["task", "list"])
    assert result.exit_code == 0
    assert "Recent Tasks" in result.stdout
    # The async worker may have already completed the task by the time we list it.
    assert any(status in result.stdout for status in ("pending", "running", "completed"))


def test_task_list_filters_by_status(patched_engine):
    runner.invoke(app, ["do", "run", "voice", "assistant", "--no-wait"])
    # The worker may transition the task through pending/running to completed before the list call.
    for status in ("pending", "running", "completed"):
        result = runner.invoke(app, ["task", "list", "--status", status])
        if "Recent Tasks" in result.stdout:
            assert status in result.stdout
            return
    pytest.fail("Task did not appear with pending, running, or completed status")


def test_task_list_no_match_shows_empty(patched_engine):
    runner.invoke(app, ["do", "run", "voice", "assistant", "--no-wait"])
    # Use a status the dispatched task will never have so the filter always returns empty.
    result = runner.invoke(app, ["task", "list", "--status", "rejected"])
    assert result.exit_code == 0
    assert "No tasks found" in result.stdout


def test_exec_invalid_json_payload(patched_engine):
    result = runner.invoke(app, ["exec", "friday", "--payload", "not-json"])
    assert result.exit_code == 1
    assert "invalid json" in result.stdout.lower()


def test_telegram_bot_requires_token(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    result = runner.invoke(app, ["telegram-bot"])
    assert result.exit_code == 1
    assert "Telegram bot token is required" in result.stdout


def test_sync_promote_stars_writes_new_modules(patched_engine, tmp_path, monkeypatch):
    """`opa sync --promote-stars` should append starred repos to the config."""
    import yaml

    from sahiixx_agency.cli.main import app as _app

    # Point OPA_CONFIG at a temp copy of the real config.
    src = (
        __import__("pathlib").Path(__file__).resolve().parents[1]
        / "config"
        / "agency.yaml"
    )
    tmp_config = tmp_path / "agency.yaml"
    tmp_config.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setenv("OPA_CONFIG", str(tmp_config))
    monkeypatch.setenv("GITHUB_TOKEN", "")

    sample_stars = [
        {
            "full_name": "google/adk-python",
            "name": "adk-python",
            "owner": "google",
            "html_url": "https://github.com/google/adk-python",
            "description": "Google Agent Development Kit for building agents",
        },
        {
            "full_name": "someuser/awesome-video-tool",
            "name": "awesome-video-tool",
            "owner": "someuser",
            "html_url": "https://github.com/someuser/awesome-video-tool",
            "description": "A tool to montage and edit videos",
        },
    ]

    async def fake_fetch(*args, **kwargs):
        return sample_stars

    monkeypatch.setattr(
        "sahiixx_agency.discovery.star_promoter.fetch_stars", fake_fetch
    )

    result = runner.invoke(_app, ["sync", "--promote-stars", "-u", "sahiixx"])
    assert result.exit_code == 0, result.stdout

    data = yaml.safe_load(tmp_config.read_text(encoding="utf-8"))
    assert "adk_python" in data["ecosystem"]
    assert "awesome_video_tool" in data["ecosystem"]
    targets = {r["target"] for r in data["routing_rules"]}
    assert "adk_python" in targets
    assert "awesome_video_tool" in targets
