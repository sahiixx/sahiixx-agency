"""Tests for the One Person Agency core."""

import asyncio

import pytest

from sahiixx_agency.core.engine import AgencyEngine
from sahiixx_agency.core.models import AgencyConfig, RepoCategory, RepoNode


def test_agency_config_loads_t3mp3st_approval_token():
    config = AgencyConfig(t3mp3st_approval_token="super-secret")
    assert config.t3mp3st_approval_token == "super-secret"

POLL_MAX_ATTEMPTS = 40
POLL_INTERVAL = 0.25

FAKE_MODULES = [
    RepoNode(
        id="echo-module",
        name="echo-module",
        full_name="sahiixx/echo-module",
        url="https://github.com/sahiixx/echo-module",
        category=RepoCategory.AGENT_FRAMEWORK,
        language="python",
        stars=10,
        capabilities=["echo"],
    ),
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


@pytest.fixture
def engine(tmp_path, monkeypatch):
    config = AgencyConfig(data_dir=str(tmp_path))
    eng = AgencyEngine(config)

    async def fake_discover(username):
        for mod in FAKE_MODULES:
            eng.registry._modules[mod.id] = mod
        return FAKE_MODULES

    async def fake_run(module, command="run", env=None, timeout=60):
        return {
            "module": module.name,
            "status": "success",
            "returncode": 0,
            "stdout": "ok",
            "stderr": "",
            "command": command,
        }

    monkeypatch.setattr(eng.registry, "discover", fake_discover)
    monkeypatch.setattr(eng.runner, "run", fake_run)
    return eng


@pytest.mark.asyncio
async def test_sync_repos(engine):
    discovered = await engine.sync_repos("sahiixx")
    assert len(discovered) == 2
    assert engine.registry.stats()["total_modules"] == 2


@pytest.mark.asyncio
async def test_dispatch_task(engine):
    await engine.start_worker()
    try:
        await engine.sync_repos("sahiixx")
        task = await engine.dispatch("run voice assistant")
        assert task.id is not None
        assert task.status.value == "pending"
        # Poll for terminal status
        for _ in range(POLL_MAX_ATTEMPTS):
            current = engine.get_task(task.id)
            if current.status.value in ("completed", "failed"):
                break
            await asyncio.sleep(POLL_INTERVAL)
        final = engine.get_task(task.id)
        assert final.status.value in ("completed", "failed")
    finally:
        await engine.stop_worker()


def test_registry_stats(engine):
    stats = engine.registry.stats()
    assert "total_modules" in stats
    assert "by_category" in stats


@pytest.mark.asyncio
async def test_intel_scout(engine, monkeypatch):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {"items": []}

    async def fake_get(self, url, **kwargs):
        return FakeResponse()

    monkeypatch.setattr("httpx.AsyncClient.get", fake_get)
    report = await engine.run_intel_scout("trending")
    assert report.id is not None
    assert len(report.repos) >= 0


@pytest.mark.asyncio
async def test_execute_module(engine):
    await engine.sync_repos("sahiixx")
    module = engine.registry.modules[0]
    result = await engine.runner.run(module, timeout=15)
    assert "status" in result
    assert result["module"] == module.name


def test_get_task_unknown_id(engine):
    assert engine.get_task("task_does_not_exist") is None


@pytest.mark.asyncio
async def test_list_tasks_returns_recent_tasks(engine):
    await engine.start_worker()
    try:
        await engine.sync_repos("sahiixx")
        task1 = await engine.dispatch("run voice assistant")
        task2 = await engine.dispatch("run voice assistant")
        tasks = engine.list_tasks(limit=10)
        ids = {t.id for t in tasks}
        assert task1.id in ids
        assert task2.id in ids
    finally:
        await engine.stop_worker()
