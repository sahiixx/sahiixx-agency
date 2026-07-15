"""Event-driven workflow engine for the agency."""

from __future__ import annotations

import contextlib
import json
import uuid
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import (
    AgencyConfig,
    AgencyTask,
    BusMessage,
    NotificationChannel,
    TaskStatus,
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowStatus,
    WorkflowStep,
    WorkflowStepState,
    WorkflowStepStatus,
)


class WorkflowEngine:
    """Define, schedule, and execute multi-step agency workflows.

    Workflows are stored as JSON files in ``workflows_dir``. The engine can run
    them manually, react to bus events, or be triggered by webhooks. Each step
    can dispatch a task, wait, send a notification, request approval, call a
    webhook, or evaluate a simple condition.
    """

    def __init__(self, config: AgencyConfig | None = None) -> None:
        self.config = config or AgencyConfig()
        self.workflows_dir = Path(self.config.workflows_dir)
        self.workflows_dir.mkdir(parents=True, exist_ok=True)
        self._definitions: dict[str, WorkflowDefinition] = {}
        self._instances: dict[str, WorkflowInstance] = {}
        self._history: deque[WorkflowInstance] = deque(maxlen=500)
        self._listeners: list[Any] = []
        self._load_definitions()

    def _load_definitions(self) -> None:
        if not self.workflows_dir.exists():
            return
        for path in sorted(self.workflows_dir.glob("*.json")):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                definition = WorkflowDefinition.model_validate(data)
                self._definitions[definition.id] = definition
            except Exception:  # noqa: BLE001
                continue

    def _save_definition(self, definition: WorkflowDefinition) -> None:
        path = self.workflows_dir / f"{definition.id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(definition.model_dump(mode="json"), f, indent=2)

    def list_definitions(self) -> list[WorkflowDefinition]:
        return list(self._definitions.values())

    def get_definition(self, workflow_id: str) -> WorkflowDefinition | None:
        return self._definitions.get(workflow_id)

    def create_definition(self, definition: WorkflowDefinition) -> WorkflowDefinition:
        definition.updated_at = datetime.now(timezone.utc)
        self._definitions[definition.id] = definition
        self._save_definition(definition)
        return definition

    def update_definition(self, workflow_id: str, updates: dict[str, Any]) -> WorkflowDefinition | None:
        definition = self._definitions.get(workflow_id)
        if definition is None:
            return None
        data = definition.model_dump(mode="json")
        data.update(updates)
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        definition = WorkflowDefinition.model_validate(data)
        self._definitions[workflow_id] = definition
        self._save_definition(definition)
        return definition

    def delete_definition(self, workflow_id: str) -> bool:
        if workflow_id not in self._definitions:
            return False
        del self._definitions[workflow_id]
        path = self.workflows_dir / f"{workflow_id}.json"
        if path.exists():
            path.unlink()
        return True

    def create_instance(
        self,
        workflow_id: str,
        context: dict[str, Any] | None = None,
    ) -> WorkflowInstance | None:
        definition = self._definitions.get(workflow_id)
        if definition is None or not definition.enabled:
            return None
        instance = WorkflowInstance(
            id=f"wfi_{uuid.uuid4().hex[:12]}",
            workflow_id=workflow_id,
            context=context or {},
            step_states=[
                WorkflowStepState(step_id=step.id)
                for step in definition.steps
            ],
        )
        self._instances[instance.id] = instance
        return instance

    def get_instance(self, instance_id: str) -> WorkflowInstance | None:
        return self._instances.get(instance_id)

    def list_instances(self, workflow_id: str | None = None, limit: int = 100) -> list[WorkflowInstance]:
        instances = list(self._instances.values())
        if workflow_id:
            instances = [i for i in instances if i.workflow_id == workflow_id]
        instances.sort(key=lambda i: i.created_at, reverse=True)
        return instances[:limit]

    async def resume_instance(
        self,
        instance_id: str,
        dispatch: Any | None = None,
        notify: Any | None = None,
    ) -> WorkflowInstance | None:
        """Resume a paused workflow instance from its current step."""
        instance = self._instances.get(instance_id)
        if instance is None or instance.status != WorkflowStatus.PAUSED:
            return None

        # Mark the pending approval step as completed so execution can continue.
        if instance.current_step_id:
            step_state = next((s for s in instance.step_states if s.step_id == instance.current_step_id), None)
            if step_state and step_state.status == WorkflowStepStatus.PENDING:
                step_state.status = WorkflowStepStatus.COMPLETED
                step_state.completed_at = datetime.now(timezone.utc)

        return await self.run_instance(instance_id, dispatch=dispatch, notify=notify)

    async def run_instance(
        self,
        instance_id: str,
        dispatch: Any | None = None,
        notify: Any | None = None,
    ) -> WorkflowInstance | None:
        """Execute a workflow instance until it pauses or completes."""
        instance = self._instances.get(instance_id)
        if instance is None:
            return None

        definition = self._definitions.get(instance.workflow_id)
        if definition is None:
            instance.status = WorkflowStatus.FAILED
            instance.error = "Workflow definition not found"
            return instance

        if instance.status in {WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED}:
            return instance

        instance.status = WorkflowStatus.RUNNING
        instance.started_at = instance.started_at or datetime.now(timezone.utc)

        try:
            step_map = {step.id: step for step in definition.steps}
            current_id = self._first_step_id(definition) if instance.current_step_id is None else instance.current_step_id

            while current_id:
                step = step_map.get(current_id)
                if step is None:
                    instance.status = WorkflowStatus.FAILED
                    instance.error = f"Step {current_id} not found"
                    break

                instance.current_step_id = current_id
                step_state = next((s for s in instance.step_states if s.step_id == current_id), None)
                if step_state is None:
                    step_state = WorkflowStepState(step_id=current_id)
                    instance.step_states.append(step_state)

                await self._run_step(instance, step, step_state, dispatch, notify)

                if step_state.status == WorkflowStepStatus.COMPLETED or step_state.status == WorkflowStepStatus.SKIPPED:
                    current_id = step.next_on_success
                else:
                    current_id = step.next_on_failure

                if step.requires_approval and step_state.status == WorkflowStepStatus.PENDING:
                    instance.status = WorkflowStatus.PAUSED
                    break

            if instance.status == WorkflowStatus.RUNNING:
                instance.status = WorkflowStatus.COMPLETED
                instance.completed_at = datetime.now(timezone.utc)
                instance.current_step_id = None
        except Exception as exc:  # noqa: BLE001
            instance.status = WorkflowStatus.FAILED
            instance.error = str(exc)

        self._history.append(instance)
        self._emit("workflow.instance.updated", {"instance": instance.model_dump(mode="json")})
        return instance

    async def _run_step(
        self,
        instance: WorkflowInstance,
        step: WorkflowStep,
        state: WorkflowStepState,
        dispatch: Any,
        notify: Any,
    ) -> None:
        state.started_at = state.started_at or datetime.now(timezone.utc)

        if step.requires_approval and state.status != WorkflowStepStatus.COMPLETED:
            state.status = WorkflowStepStatus.PENDING
            self._emit(
                "workflow.step.awaiting_approval",
                {"instance_id": instance.id, "step_id": step.id},
            )
            return

        state.status = WorkflowStepStatus.RUNNING

        try:
            if step.action == "dispatch":
                if dispatch is None:
                    raise RuntimeError("Dispatch function not provided")
                intent = self._render_template(step.intent_template or step.name, instance.context)
                payload = {**step.payload, "workflow_instance_id": instance.id}
                task = await dispatch(intent, payload)
                if isinstance(task, AgencyTask):
                    state.task_id = task.id
                    state.result = {"task_id": task.id, "status": task.status.value}
                    if task.status == TaskStatus.FAILED:
                        state.status = WorkflowStepStatus.FAILED
                        state.error = task.error or "Task failed"
                    else:
                        state.status = WorkflowStepStatus.COMPLETED
                else:
                    state.result = task
                    state.status = WorkflowStepStatus.COMPLETED
            elif step.action == "notify":
                if notify is not None:
                    await notify(
                        NotificationChannel(step.payload.get("channel", "sse")),
                        self._render_template(step.payload.get("title", "Workflow notification"), instance.context),
                        self._render_template(step.payload.get("body", step.name), instance.context),
                    )
                state.status = WorkflowStepStatus.COMPLETED
            elif step.action == "wait":
                seconds = float(step.payload.get("seconds", 0))
                if seconds > 0:
                    await __import__("asyncio").sleep(seconds)
                state.status = WorkflowStepStatus.COMPLETED
            elif step.action == "webhook":
                result = await self._run_webhook_step(step, instance)
                state.result = result
                state.status = WorkflowStepStatus.COMPLETED if result.get("ok") else WorkflowStepStatus.FAILED
            elif step.action == "condition":
                if self._evaluate_condition(step.condition, instance.context):
                    state.status = WorkflowStepStatus.COMPLETED
                else:
                    state.status = WorkflowStepStatus.SKIPPED
            elif step.action == "noop":
                state.status = WorkflowStepStatus.COMPLETED
            else:
                state.status = WorkflowStepStatus.COMPLETED
        except Exception as exc:  # noqa: BLE001
            state.status = WorkflowStepStatus.FAILED
            state.error = str(exc)
        finally:
            state.completed_at = datetime.now(timezone.utc)

    async def _run_webhook_step(self, step: WorkflowStep, instance: WorkflowInstance) -> dict[str, Any]:
        import httpx

        url = step.payload.get("url")
        method = step.payload.get("method", "POST").upper()
        headers = step.payload.get("headers", {})
        body = self._render_json(step.payload.get("body", {}), instance.context)

        if not url:
            return {"ok": False, "error": "Missing webhook URL"}

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                if method == "GET":
                    resp = await client.get(url, headers=headers, params=body)
                else:
                    resp = await client.request(method, url, headers=headers, json=body)
            return {"ok": resp.status_code < 400, "status_code": resp.status_code, "body": resp.text[:500]}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def _evaluate_condition(self, condition: str | None, context: dict[str, Any]) -> bool:
        if not condition:
            return True
        # Very small safe evaluator for simple comparisons.
        try:
            return bool(eval(condition, {"__builtins__": {}}, context))  # noqa: S307
        except Exception:  # noqa: BLE001
            return False

    @staticmethod
    def _render_template(template: str | None, context: dict[str, Any]) -> str:
        if template is None:
            return ""
        result = template
        for key, value in context.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result

    @staticmethod
    def _render_json(data: Any, context: dict[str, Any]) -> Any:
        if isinstance(data, str):
            return WorkflowEngine._render_template(data, context)
        if isinstance(data, dict):
            return {k: WorkflowEngine._render_json(v, context) for k, v in data.items()}
        if isinstance(data, list):
            return [WorkflowEngine._render_json(v, context) for v in data]
        return data

    def _first_step_id(self, definition: WorkflowDefinition) -> str | None:
        if not definition.steps:
            return None
        # Find a step that is not referenced as next by another step.
        referenced = {
            s.next_on_success for s in definition.steps if s.next_on_success
        } | {s.next_on_failure for s in definition.steps if s.next_on_failure}
        for step in definition.steps:
            if step.id not in referenced:
                return step.id
        return definition.steps[0].id

    def _emit(self, topic: str, payload: dict[str, Any]) -> None:
        message = BusMessage(
            id=f"msg_{uuid.uuid4().hex[:8]}",
            topic=topic,
            sender="workflow_engine",
            payload=payload,
        )
        for listener in list(self._listeners):
            with contextlib.suppress(Exception):
                listener(message)

    def subscribe(self, listener: Any) -> None:
        self._listeners.append(listener)

    def seed_defaults(self) -> list[WorkflowDefinition]:
        """Create a few useful default workflows if none exist."""
        if self._definitions:
            return []

        trending_pipeline = WorkflowDefinition(
            id="trending-content-pipeline",
            name="Trending Content Pipeline",
            description="Discover trending repos, sync them into the registry, and notify the operator",
            trigger="schedule",
            schedule="0 6 * * *",
            steps=[
                WorkflowStep(
                    id="discover",
                    name="Discover trending repos",
                    action="dispatch",
                    target="discovery",
                    intent_template="discover trending repos",
                    payload={"report_type": "trending", "min_stars": 100},
                    next_on_success="sync",
                ),
                WorkflowStep(
                    id="sync",
                    name="Sync discovered repos into registry",
                    action="dispatch",
                    target="agency",
                    intent_template="sync github repos into the registry",
                    next_on_success="notify",
                ),
                WorkflowStep(
                    id="notify",
                    name="Notify operator",
                    action="notify",
                    payload={
                        "channel": "sse",
                        "title": "Trending pipeline complete",
                        "body": "Discovery scout ran and the registry sync was queued for review.",
                    },
                ),
            ],
        )
        self.create_definition(trending_pipeline)
        return [trending_pipeline]
