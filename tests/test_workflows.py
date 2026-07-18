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


@pytest.mark.asyncio
async def test_seed_trending_pipeline_runs_end_to_end(engine):
    """The seeded trending pipeline should discover -> sync -> notify successfully."""
    seeded = engine.seed_defaults()
    assert any(d.id == "trending-content-pipeline" for d in seeded)

    definition = engine.get_definition("trending-content-pipeline")
    assert definition is not None
    # The discovery step must target a routable module (regression guard against
    # the old broken "run discovery pipeline" intent that routed to None).
    discover_step = next(s for s in definition.steps if s.id == "discover")
    assert discover_step.target == "discovery"

    dispatched: list[str] = []

    async def fake_dispatch(intent, payload):
        dispatched.append(intent)
        return {"intent": intent, "payload": payload, "status": "completed"}

    notified: list[str] = []

    async def fake_notify(channel, title, body):
        notified.append(title)

    instance = engine.create_instance("trending-content-pipeline")
    assert instance is not None
    result = await engine.run_instance(instance.id, dispatch=fake_dispatch, notify=fake_notify)
    assert result is not None
    assert result.status == WorkflowStatus.COMPLETED
    # All three steps completed in order.
    states = {s.step_id: s.status for s in result.step_states}
    assert states["discover"] == WorkflowStepStatus.COMPLETED
    assert states["sync"] == WorkflowStepStatus.COMPLETED
    assert states["notify"] == WorkflowStepStatus.COMPLETED
    assert len(dispatched) == 2
    assert notified == ["Trending pipeline complete"]


@pytest.mark.asyncio
async def test_trigger_event_runs_matching_workflows(engine):
    definition = WorkflowDefinition(
        id="event-wf",
        name="Event Workflow",
        trigger="event",
        event_topic="task.completed",
        steps=[
            WorkflowStep(id="react", name="React", action="dispatch", intent_template="process {{task_id}}"),
        ],
    )
    engine.create_definition(definition)

    async def fake_dispatch(intent, payload):
        return {"intent": intent, "payload": payload}

    instances = await engine.trigger_event("task.completed", {"task_id": "task_123"}, dispatch=fake_dispatch)
    assert len(instances) == 1
    assert instances[0].status == WorkflowStatus.COMPLETED


@pytest.mark.asyncio
async def test_trigger_event_ignores_non_matching_topic(engine):
    definition = WorkflowDefinition(
        id="event-wf",
        name="Event Workflow",
        trigger="event",
        event_topic="task.completed",
        steps=[WorkflowStep(id="react", name="React", action="noop")],
    )
    engine.create_definition(definition)

    instances = await engine.trigger_event("task.failed", {"task_id": "task_123"})
    assert len(instances) == 0


@pytest.mark.asyncio
async def test_trigger_webhook_runs_workflow(engine):
    definition = WorkflowDefinition(
        id="webhook-wf",
        name="Webhook Workflow",
        trigger="webhook",
        steps=[
            WorkflowStep(id="process", name="Process", action="dispatch", intent_template="handle webhook {{webhook.action}}"),
        ],
    )
    engine.create_definition(definition)

    async def fake_dispatch(intent, payload):
        return {"intent": intent, "payload": payload}

    result = await engine.trigger_webhook("webhook-wf", {"action": "push"}, dispatch=fake_dispatch)
    assert result is not None
    assert result.status == WorkflowStatus.COMPLETED


@pytest.mark.asyncio
async def test_trigger_webhook_returns_none_for_missing_workflow(engine):
    result = await engine.trigger_webhook("missing-wf", {})
    assert result is None


def test_portfolio_publisher_workflow_definition():
    import json

    with open("data/workflows/portfolio-publisher.json", encoding="utf-8") as fh:
        definition = WorkflowDefinition.model_validate(json.load(fh))
    assert definition.id == "portfolio-publisher"
    assert definition.trigger == "event"
    assert definition.event_topic == "registry.module_added"
    assert definition.enabled is True
    assert len(definition.steps) == 1
    step = definition.steps[0]
    assert step.action == "dispatch"
    assert step.requires_approval is False
    assert "{name}" in (step.intent_template or "")


def test_render_json_substitutes_context_in_payload():
    rendered = WorkflowEngine._render_json(
        {"module_id": "{id}", "nested": ["{name}"], "n": 1},
        {"id": "x1", "name": "n1"},
    )
    assert rendered == {"module_id": "x1", "nested": ["n1"], "n": 1}
