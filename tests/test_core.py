"""Tests for the One Person Agency core."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from sahiixx_agency.core.engine import AgencyEngine
from sahiixx_agency.core.models import AgencyConfig, RepoCategory, RepoNode, TaskStatus
from sahiixx_agency.core.registry import RepoRegistry


def _fake_repo(name: str, category: RepoCategory = RepoCategory.AGENT_FRAMEWORK) -> RepoNode:
    """Return a deterministic RepoNode for offline tests."""
    return RepoNode(
        id=name,
        name=name,
        full_name=f"sahiixx/{name}",
        description=f"A fake {name} repo",
        url=f"https://github.com/sahiixx/{name}",
        category=category,
        language="Python",
        stars=10,
        forks=1,
    )


def _seed_registry(registry: RepoRegistry, *repos: RepoNode) -> None:
    """Populate registry modules directly, bypassing network calls."""
    for repo in repos:
        registry._modules[repo.id] = repo


@pytest.fixture
def engine(tmp_path: Path) -> AgencyEngine:
    config = AgencyConfig(data_dir=str(tmp_path))
    return AgencyEngine(config)


@pytest.mark.asyncio
async def test_sync_repos(engine: AgencyEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _fake_repo("voice-assistant")
    _seed_registry(engine.registry, fake)
    discover_mock = AsyncMock(return_value=[fake])
    monkeypatch.setattr(engine.registry, "discover", discover_mock)
    discovered = await engine.sync_repos("sahiixx")
    assert len(discovered) > 0
    assert engine.registry.stats()["total_modules"] > 0
    discover_mock.assert_awaited_once_with("sahiixx")


@pytest.mark.asyncio
async def test_dispatch_task(engine: AgencyEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _fake_repo("voice-assistant")
    _seed_registry(engine.registry, fake)
    monkeypatch.setattr(
        engine.registry,
        "discover",
        AsyncMock(return_value=[fake]),
    )
    monkeypatch.setattr(
        engine.runner,
        "run",
        AsyncMock(return_value={"status": "success", "module": fake.name}),
    )
    task = await engine.dispatch("run voice assistant")
    assert task.id is not None
    assert task.status.value in ("running", "completed", "failed")


def test_registry_stats(engine: AgencyEngine) -> None:
    stats = engine.registry.stats()
    assert "total_modules" in stats
    assert "by_category" in stats


@pytest.mark.asyncio
async def test_intel_scout(engine: AgencyEngine) -> None:
    report = await engine.run_intel_scout("trending")
    assert report.id is not None
    assert len(report.repos) >= 0


@pytest.mark.asyncio
async def test_execute_module(engine: AgencyEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _fake_repo("voice-assistant")
    _seed_registry(engine.registry, fake)
    monkeypatch.setattr(
        engine.registry,
        "discover",
        AsyncMock(return_value=[fake]),
    )
    await engine.sync_repos("sahiixx")
    module = engine.registry.modules[0]
    monkeypatch.setattr(
        engine.runner,
        "run",
        AsyncMock(return_value={"status": "success", "module": module.name}),
    )
    result = await engine.runner.run(module, timeout=15)
    assert "status" in result
    assert result["module"] == module.name


@pytest.mark.asyncio
async def test_submit_task_creates_pending_task(engine: AgencyEngine) -> None:
    task = await engine.submit_task("noop test task")
    assert task.id is not None
    assert task.status == TaskStatus.PENDING
    assert engine.get_task(task.id) is task


@pytest.mark.asyncio
async def test_worker_processes_queued_task(engine: AgencyEngine) -> None:
    await engine.start_worker()
    try:
        task = await engine.submit_task("noop test task")
        await engine._task_queue.join()
        fetched = engine.get_task(task.id)
        assert fetched is not None
        assert fetched.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
    finally:
        await engine.stop_worker()


@pytest.mark.asyncio
async def test_list_tasks_returns_recent_tasks(engine: AgencyEngine) -> None:
    task = await engine.submit_task("noop test task")
    tasks = engine.list_tasks(limit=10)
    assert task in tasks
    assert tasks[0].id == task.id


@pytest.mark.asyncio
async def test_scheduler_starts_and_stops(engine: AgencyEngine) -> None:
    status = engine.scheduler_status()
    assert status["running"] is False
    await engine.start_scheduler(interval_minutes=5)
    status = engine.scheduler_status()
    assert status["running"] is True
    assert status["interval_minutes"] == 5
    assert status["next_sync_at"] is not None
    await engine.stop_scheduler()
    status = engine.scheduler_status()
    assert status["running"] is False


@pytest.mark.asyncio
async def test_scheduler_triggers_sync(engine: AgencyEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    sync_event = asyncio.Event()

    async def fake_sync(username: str | None = None) -> list[RepoNode]:
        sync_event.set()
        return []

    monkeypatch.setattr(engine, "sync_repos", fake_sync)
    await engine.start_scheduler(interval_minutes=0.001)
    try:
        await asyncio.wait_for(sync_event.wait(), timeout=1.0)
    finally:
        await engine.stop_scheduler()


@pytest.mark.asyncio
async def test_scheduler_status_reports_state(engine: AgencyEngine) -> None:
    status = engine.scheduler_status()
    assert status["running"] is False
    assert status["interval_minutes"] == 60
    assert status["last_sync_at"] is None
    assert status["next_sync_at"] is None
    await engine.start_scheduler(interval_minutes=10)
    status = engine.scheduler_status()
    assert status["running"] is True
    assert status["interval_minutes"] == 10
    assert status["next_sync_at"] is not None
    await engine.stop_scheduler()
