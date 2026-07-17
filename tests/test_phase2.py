"""Tests for Phase 2 autonomy scaffolding: scheduler and long-term memory."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from sahiixx_agency.core.engine import AgencyEngine
from sahiixx_agency.core.ltm import LongTermMemory
from sahiixx_agency.core.models import AgencyConfig
from sahiixx_agency.core.scheduler import ScheduledWorkflow, WorkflowScheduler


@pytest.fixture
def engine(tmp_path: pytest.TempPathFactory) -> AgencyEngine:
    return AgencyEngine(AgencyConfig(data_dir=str(tmp_path), memory_backend="json"))


def test_long_term_memory_recall(engine: AgencyEngine) -> None:
    ltm = LongTermMemory(engine.memory)
    mid = ltm.remember("Deploy landing page for Pulse", topic="projects", source_id="task_abc")
    assert mid.startswith("mem_")
    results = ltm.recall(topic="projects")
    assert len(results) == 1
    assert results[0]["content"] == "Deploy landing page for Pulse"


def test_long_term_memory_forget(engine: AgencyEngine) -> None:
    ltm = LongTermMemory(engine.memory)
    mid = ltm.remember("Test memory")
    assert ltm.forget(mid) is True
    assert ltm.forget(mid) is False
    assert len(ltm.recall()) == 0


def test_scheduler_save_and_list(engine: AgencyEngine) -> None:
    scheduler = WorkflowScheduler(engine)
    schedule = ScheduledWorkflow(workflow_id="wf_1", interval_seconds=60)
    scheduler.save_schedule(schedule)
    assert len(scheduler.list_schedules()) == 1
    assert schedule.next_run_at is not None


def test_scheduler_delete(engine: AgencyEngine) -> None:
    scheduler = WorkflowScheduler(engine)
    schedule = ScheduledWorkflow(workflow_id="wf_1", interval_seconds=60)
    scheduler.save_schedule(schedule)
    assert scheduler.delete_schedule(schedule.id) is True
    assert scheduler.delete_schedule(schedule.id) is False


def test_scheduler_loads_from_memory(engine: AgencyEngine) -> None:
    scheduler = WorkflowScheduler(engine)
    schedule = ScheduledWorkflow(workflow_id="wf_1", interval_seconds=60)
    scheduler.save_schedule(schedule)

    scheduler2 = WorkflowScheduler(engine)
    scheduler2.load_schedules()
    assert len(scheduler2.list_schedules()) == 1


@pytest.mark.asyncio
async def test_scheduler_tick_triggers_workflow(engine: AgencyEngine) -> None:
    from sahiixx_agency.core.models import WorkflowDefinition, WorkflowStep

    engine.workflows._definitions["wf_1"] = WorkflowDefinition(
        id="wf_1",
        name="Test Workflow",
        steps=[WorkflowStep(id="step_1", name="Step 1", type="noop")],
    )
    scheduler = WorkflowScheduler(engine, poll_interval_seconds=0.1)
    schedule = ScheduledWorkflow(workflow_id="wf_1", interval_seconds=1)
    scheduler.save_schedule(schedule)

    await scheduler.start()
    # Force next run in the past
    schedule.next_run_at = datetime.now(timezone.utc)
    scheduler.save_schedule(schedule)
    await asyncio.sleep(0.3)
    await scheduler.stop()

    assert schedule.last_run_at is not None
    assert schedule.next_run_at > schedule.last_run_at


def test_scheduler_sync_from_workflow_definitions(engine: AgencyEngine) -> None:
    from sahiixx_agency.core.models import WorkflowDefinition, WorkflowStep

    definition = WorkflowDefinition(
        id="scheduled-wf",
        name="Scheduled Workflow",
        trigger="schedule",
        schedule="0 6 * * *",
        steps=[WorkflowStep(id="step_1", name="Step 1", action="noop")],
    )
    engine.workflows.create_definition(definition)

    scheduler = WorkflowScheduler(engine)
    scheduler.sync_from_workflow_definitions()

    schedules = scheduler.list_schedules()
    found = next((s for s in schedules if s.workflow_id == "scheduled-wf"), None)
    assert found is not None
    assert found.next_run_at is not None


def test_scheduler_load_parses_iso_datetimes(engine: AgencyEngine) -> None:
    scheduler = WorkflowScheduler(engine)
    schedule = ScheduledWorkflow(workflow_id="wf_iso", interval_seconds=60)
    scheduler.save_schedule(schedule)

    # Simulate a fresh engine instance reading the same memory
    scheduler2 = WorkflowScheduler(engine)
    scheduler2.load_schedules()
    loaded = scheduler2.list_schedules()
    assert len(loaded) == 1
    assert isinstance(loaded[0].next_run_at, datetime)
    assert isinstance(loaded[0].created_at, datetime)
