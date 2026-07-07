"""Tests for the workflow engine."""

from __future__ import annotations

import pytest

from sahiixx_agency.core.models import (
    WorkflowDefinition,
    WorkflowStatus,
    WorkflowStep,
    WorkflowStepStatus,
)
from sahiixx_agency.core.workflows import WorkflowEngine


@pytest.fixture
def engine(tmp_path):
    from sahiixx_agency.core.models import AgencyConfig

    config = AgencyConfig(data_dir=str(tmp_path), workflows_dir=str(tmp_path / "workflows"))
    return WorkflowEngine(config=config)


@pytest.mark.asyncio
async def test_create_and_run_dispatch_workflow(engine):
    definition = WorkflowDefinition(
        id="test-dispatch",
        name="Test Dispatch",
        steps=[
            WorkflowStep(id="step1", name="Run echo", action="dispatch", intent_template="echo hello", next_on_success="step2"),
            WorkflowStep(id="step2", name="Notify", action="notify", payload={"channel": "sse", "title": "Done", "body": "Workflow done"}),
        ],
    )
    engine.create_definition(definition)

    async def fake_dispatch(intent, payload):
        return {"intent": intent, "payload": payload}

    async def fake_notify(channel, title, body):
        pass

    instance = engine.create_instance("test-dispatch")
    assert instance is not None
    result = await engine.run_instance(instance.id, dispatch=fake_dispatch, notify=fake_notify)
    assert result is not None
    assert result.status == WorkflowStatus.COMPLETED


@pytest.mark.asyncio
async def test_workflow_condition_skips_step(engine):
    definition = WorkflowDefinition(
        id="test-condition",
        name="Test Condition",
        steps=[
            WorkflowStep(id="check", name="Check", action="condition", condition="skip == True", next_on_success="yes", next_on_failure="no"),
            WorkflowStep(id="yes", name="Yes"),
            WorkflowStep(id="no", name="No"),
        ],
    )
    engine.create_definition(definition)
    instance = engine.create_instance("test-condition", context={"skip": True})
    result = await engine.run_instance(instance.id)
    assert result is not None
    assert result.status == WorkflowStatus.COMPLETED
    states = {s.step_id: s.status for s in result.step_states}
    assert states["check"] == WorkflowStepStatus.COMPLETED
    assert states["yes"] == WorkflowStepStatus.COMPLETED
    assert states["no"] == WorkflowStepStatus.PENDING


@pytest.mark.asyncio
async def test_workflow_not_found_returns_none(engine):
    assert engine.create_instance("missing") is None


def test_list_workflows(engine):
    engine.create_definition(WorkflowDefinition(id="wf1", name="One"))
    engine.create_definition(WorkflowDefinition(id="wf2", name="Two"))
    workflows = engine.list_definitions()
    assert len(workflows) == 2


def test_delete_workflow(engine):
    engine.create_definition(WorkflowDefinition(id="wf1", name="One"))
    assert engine.delete_definition("wf1") is True
    assert engine.get_definition("wf1") is None
    assert engine.delete_definition("wf1") is False


@pytest.mark.asyncio
async def test_workflow_webhook_step(engine):
    definition = WorkflowDefinition(
        id="test-webhook",
        name="Test Webhook",
        steps=[
            WorkflowStep(
                id="hook",
                name="Call hook",
                action="webhook",
                payload={"url": "http://localhost:9999/invalid", "method": "POST", "body": {}},
            ),
        ],
    )
    engine.create_definition(definition)
    instance = engine.create_instance("test-webhook")
    result = await engine.run_instance(instance.id)
    assert result is not None
    assert result.status == WorkflowStatus.COMPLETED
    hook_state = next(s for s in result.step_states if s.step_id == "hook")
    assert hook_state.status == WorkflowStepStatus.FAILED
    assert hook_state.result is not None
    assert hook_state.result.get("ok") is False
