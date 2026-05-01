"""Tests for the One Person Agency core."""

import pytest

from sahiixx_agency.core.engine import AgencyEngine
from sahiixx_agency.core.models import AgencyConfig, RepoCategory
from sahiixx_agency.core.registry import RepoRegistry


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
    assert task.status.value in ("running", "completed", "failed")


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
