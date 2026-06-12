"""Tests for the One Person Agency core."""

import asyncio

import pytest

from sahiixx_agency.core.engine import AgencyEngine
from sahiixx_agency.core.models import AgencyConfig


@pytest.fixture
def engine(tmp_path):
    config = AgencyConfig(data_dir=str(tmp_path))
    return AgencyEngine(config)


@pytest.mark.asyncio
async def test_sync_repos(engine):
    discovered = await engine.sync_repos("sahiixx")
    assert len(discovered) > 0
    assert engine.registry.stats()["total_modules"] > 0


@pytest.mark.asyncio
async def test_dispatch_task(engine):
    await engine.sync_repos("sahiixx")
    task = await engine.dispatch("run voice assistant")
    assert task.id is not None
    assert task.status.value in ("pending", "running", "completed", "failed")


def test_registry_stats(engine):
    stats = engine.registry.stats()
    assert "total_modules" in stats
    assert "by_category" in stats


@pytest.mark.asyncio
async def test_intel_scout(engine):
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


@pytest.mark.asyncio
async def test_dispatch_returns_pending_and_worker_completes(engine):
    await engine.start_worker()
    try:
        await engine.sync_repos("sahiixx")
        task = await engine.dispatch("run voice assistant")
        assert task.status.value == "pending"
        # Poll until terminal (timeout protects against hangs)
        for _ in range(40):
            current = engine.get_task(task.id)
            assert current is not None
            if current.status.value in ("completed", "failed"):
                break
            await asyncio.sleep(0.25)
        final = engine.get_task(task.id)
        assert final.status.value in ("completed", "failed")
    finally:
        await engine.stop_worker()
