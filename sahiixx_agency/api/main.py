"""FastAPI server for the One Person Agency."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated, Any

import httpx
from fastapi import Body, Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from sahiixx_agency.core.engine import AgencyEngine
from sahiixx_agency.core.models import (
    AgencyConfig,
    AgencyTask,
    LLMMessage,
    NotificationChannel,
    RepoCategory,
    TaskLogEntry,
    TaskStatus,
    WorkflowDefinition,
)

_engine: AgencyEngine | None = None


def get_engine() -> AgencyEngine:
    if _engine is None:
        raise RuntimeError("Engine not initialized")
    return _engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _engine
    config_path = os.environ.get("OPA_CONFIG", "./config/agency.yaml")
    config = AgencyConfig()
    if os.path.exists(config_path):
        import yaml

        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        config = AgencyConfig.model_validate(data)
    _engine = AgencyEngine(config)
    await _engine.start_worker()
    # Auto-sync on startup if registry is empty
    if not _engine.registry.modules:
        await _engine.sync_repos(config.github_username)
    yield
    await _engine.stop_worker()
    _engine = None


app = FastAPI(
    title="One Person Agency",
    description="Unified AI orchestration for all repos",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def api_prefix_middleware(request: Request, call_next: Any) -> Any:
    """Allow dashboard to call /api/* while backend routes live at /*."""
    scope = request.scope
    path = scope.get("path", "")
    if path.startswith("/api/"):
        new_path = path[4:]  # strip /api
        scope["path"] = new_path
        raw_path = scope.get("raw_path", b"")
        if raw_path.startswith(b"/api/"):
            scope["raw_path"] = raw_path[4:]
    return await call_next(request)


# ---------- Health & Status ----------


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": "One Person Agency", "version": "1.0.0", "status": "running"}


@app.get("/health")
async def health(engine: Annotated[AgencyEngine, Depends(get_engine)]) -> dict[str, Any]:
    checks = engine.metrics.health()
    return {
        "status": engine.metrics.overall_health().value,
        "registry_count": len(engine.registry.modules),
        "checks": [c.model_dump(mode="json") for c in checks],
    }


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics(engine: Annotated[AgencyEngine, Depends(get_engine)]) -> str:
    """Prometheus-compatible metrics endpoint."""
    return engine.metrics.to_prometheus()


@app.get("/stats")
async def stats(engine: Annotated[AgencyEngine, Depends(get_engine)]) -> dict[str, Any]:
    return engine.stats()


# ---------- Registry ----------


@app.get("/registry")
async def list_registry(
    engine: Annotated[AgencyEngine, Depends(get_engine)],
    category: str | None = Query(None),
    language: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[dict[str, Any]]:
    modules = engine.registry.modules
    if category:
        try:
            cat = RepoCategory(category)
            modules = [m for m in modules if m.category == cat]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown category: {category}") from None
    if language:
        modules = [m for m in modules if m.language and m.language.lower() == language.lower()]
    modules.sort(key=lambda m: m.stars, reverse=True)
    return [m.model_dump(mode="json") for m in modules[offset : offset + limit]]


@app.get("/registry/{module_id}")
async def get_module(module_id: str, engine: Annotated[AgencyEngine, Depends(get_engine)]) -> dict[str, Any]:
    mod = engine.registry.get(module_id)
    if not mod:
        raise HTTPException(status_code=404, detail="Module not found")
    return mod.model_dump(mode="json")


@app.post("/registry/sync")
async def sync_registry(
    engine: Annotated[AgencyEngine, Depends(get_engine)],
    username: str | None = Query(None),
) -> dict[str, Any]:
    discovered = await engine.sync_repos(username or engine.config.github_username)
    return {"synced": len(discovered), "username": username or engine.config.github_username}


# ---------- Tasks ----------


class DispatchRequest(BaseModel):
    intent: str
    payload: dict[str, Any] = Field(default_factory=dict)


@app.post("/tasks")
async def create_task(
    intent: str,
    engine: Annotated[AgencyEngine, Depends(get_engine)],
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    task = await engine.dispatch(intent, payload)
    return task.model_dump(mode="json")


@app.post("/dispatch")
async def dispatch_json(
    request: DispatchRequest,
    engine: Annotated[AgencyEngine, Depends(get_engine)],
) -> dict[str, Any]:
    """Dispatch a task with a JSON body containing intent and payload."""
    task = await engine.dispatch(request.intent, request.payload)
    return task.model_dump(mode="json")


@app.get("/tasks")
async def list_tasks(
    engine: Annotated[AgencyEngine, Depends(get_engine)],
    limit: int = Query(50, ge=1, le=200),
) -> list[dict[str, Any]]:
    tasks = engine.list_tasks(limit=limit)
    output: list[dict[str, Any]] = []
    for t in tasks:
        data = t.model_dump(mode="json")
        # Dashboard TaskStream expects `module` as a display alias.
        data["module"] = data.get("module_id")
        output.append(data)
    return output


class ExecuteModuleRequest(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)
    tenant_id: str | None = Field(default=None)
    project_id: str | None = Field(default=None)


@app.post("/tasks/{module_id:path}/execute")
async def execute_module(
    module_id: str,
    engine: Annotated[AgencyEngine, Depends(get_engine)],
    request: ExecuteModuleRequest | None = None,
    command: str = Query("run"),
    timeout: int = Query(120, ge=1, le=600),
) -> dict[str, Any]:
    """Clone, inspect, and execute a specific module through the task lifecycle."""
    mod = engine.registry.get(module_id)
    if not mod:
        raise HTTPException(status_code=404, detail="Module not found")

    request = request or ExecuteModuleRequest()
    payload = dict(request.payload)
    payload.setdefault("command", command)
    payload.setdefault("timeout", timeout)

    task = AgencyTask(
        id=f"task_{__import__('uuid').uuid4().hex[:12]}",
        intent=f"direct execute {module_id}",
        module_id=module_id,
        category=mod.category,
        payload=payload,
        tenant_id=request.tenant_id,
        project_id=request.project_id,
    )
    engine._tasks[task.id] = task
    engine.memory.log_event("task.created", {"task_id": task.id, "intent": task.intent})
    engine._persist_task(task)
    engine.audit.log(
        "task.dispatched",
        "operator",
        task.id,
        {"intent": task.intent, "module_id": task.module_id, "category": task.category.value if task.category else None},
    )
    await engine.task_logger.info(
        task.id,
        "Task dispatched",
        actor="engine",
        **{
            "intent": task.intent,
            "module_id": task.module_id,
            "category": task.category.value if task.category else None,
        },
    )
    await engine._task_queue.put(task)

    # Poll for terminal status so the endpoint remains synchronous for callers.
    terminal_statuses = {"completed", "failed", "cancelled"}
    for _ in range(60):
        current = engine.get_task(task.id)
        if current and current.status.value in terminal_statuses:
            break
        await asyncio.sleep(0.1)

    final = engine.get_task(task.id)
    return {
        "task_id": final.id,
        "module": module_id,
        "command": command,
        "timeout": timeout,
        "status": final.status.value,
        "result": final.result,
        "error": final.error,
    }


@app.get("/tasks/{task_id}")
async def get_task(task_id: str, engine: Annotated[AgencyEngine, Depends(get_engine)]) -> dict[str, Any]:
    task = engine.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.model_dump(mode="json")


@app.get("/tasks/{task_id}/logs")
async def get_task_logs(
    task_id: str,
    engine: Annotated[AgencyEngine, Depends(get_engine)],
) -> list[dict[str, Any]]:
    """Return structured log entries for a task.

    Returns an empty list if the task has no log file yet.
    """
    entries = await engine.task_logger.read(task_id)
    return [TaskLogEntry.model_validate(e).model_dump(mode="json") for e in entries]


@app.post("/tasks/{task_id}/approve")
async def approve_task(
    task_id: str,
    engine: Annotated[AgencyEngine, Depends(get_engine)],
) -> dict[str, Any]:
    """Approve a pending high-risk task and re-queue it for execution."""
    task = engine.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    req = await engine.approve_task(task_id, by="dashboard")
    if req is None:
        raise HTTPException(status_code=400, detail="No approval request for task")
    await engine._task_queue.put(task)
    return {"status": "approved", "request_id": req.id}


@app.post("/tasks/{task_id}/reject")
async def reject_task(
    task_id: str,
    engine: Annotated[AgencyEngine, Depends(get_engine)],
) -> dict[str, Any]:
    """Reject a pending high-risk task."""
    task = engine.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    req = await engine.reject_task(task_id, by="dashboard")
    if req is None:
        raise HTTPException(status_code=400, detail="No approval request for task")
    task.status = TaskStatus.CANCELLED
    return {"status": "rejected", "request_id": req.id}


# ---------- Approvals ----------


@app.get("/approvals")
async def list_approvals(
    engine: Annotated[AgencyEngine, Depends(get_engine)],
    status: str | None = Query(None),
) -> list[dict[str, Any]]:
    """List approval requests, optionally filtered by status."""
    requests = list(engine.approval_manager._requests.values())
    if status:
        requests = [r for r in requests if r.status == status]
    return [r.model_dump(mode="json") for r in sorted(requests, key=lambda r: r.requested_at, reverse=True)]


@app.get("/approvals/pending")
async def list_pending_approvals(
    engine: Annotated[AgencyEngine, Depends(get_engine)],
) -> list[dict[str, Any]]:
    """Return pending approvals formatted for the dashboard queue."""
    pending = engine.list_pending_approvals()
    return [
        {
            "id": req.id,
            "task_id": req.task_id,
            "title": req.reason or "Approval requested",
            "description": f"Risk level: {req.risk_level.value}",
            "requester": "agency",
            "risk_level": req.risk_level.value,
            "created_at": req.requested_at.isoformat(),
        }
        for req in pending
    ]


@app.post("/approvals/{approval_id}/approve")
async def approve_by_id(
    approval_id: str,
    engine: Annotated[AgencyEngine, Depends(get_engine)],
) -> dict[str, Any]:
    """Approve a specific approval request by id and re-queue its task."""
    req = engine.approval_manager.approve(approval_id, by="dashboard")
    if req is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    task = engine.get_task(req.task_id)
    if task is not None:
        await engine._task_queue.put(task)
    return {"status": "approved", "request_id": req.id}


@app.post("/approvals/{approval_id}/reject")
async def reject_by_id(
    approval_id: str,
    engine: Annotated[AgencyEngine, Depends(get_engine)],
) -> dict[str, Any]:
    """Reject a specific approval request by id."""
    req = engine.approval_manager.reject(approval_id, by="dashboard")
    if req is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    task = engine.get_task(req.task_id)
    if task is not None:
        task.status = TaskStatus.CANCELLED
    return {"status": "rejected", "request_id": req.id}


# ---------- Workflows ----------


class WorkflowRunRequest(BaseModel):
    context: dict[str, Any] = Field(default_factory=dict)


@app.get("/workflows")
async def list_workflows(
    engine: Annotated[AgencyEngine, Depends(get_engine)],
) -> list[dict[str, Any]]:
    """List all workflow definitions."""
    return [w.model_dump(mode="json") for w in engine.workflows.list_definitions()]


@app.post("/workflows")
async def create_workflow(
    definition: WorkflowDefinition,
    engine: Annotated[AgencyEngine, Depends(get_engine)],
) -> dict[str, Any]:
    """Create or update a workflow definition."""
    created = engine.workflows.create_definition(definition)
    return created.model_dump(mode="json")


@app.get("/workflows/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    engine: Annotated[AgencyEngine, Depends(get_engine)],
) -> dict[str, Any]:
    """Get a workflow definition by id."""
    definition = engine.workflows.get_definition(workflow_id)
    if definition is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return definition.model_dump(mode="json")


@app.delete("/workflows/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    engine: Annotated[AgencyEngine, Depends(get_engine)],
) -> dict[str, str]:
    """Delete a workflow definition."""
    if not engine.workflows.delete_definition(workflow_id):
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"status": "deleted", "workflow_id": workflow_id}


@app.post("/workflows/{workflow_id}/run")
async def run_workflow(
    workflow_id: str,
    request: Annotated[WorkflowRunRequest, Body(default_factory=WorkflowRunRequest)],
    engine: Annotated[AgencyEngine, Depends(get_engine)],
) -> dict[str, Any]:
    """Create and run a workflow instance."""
    instance = engine.workflows.create_instance(workflow_id, request.context)
    if instance is None:
        raise HTTPException(status_code=404, detail="Workflow not found or disabled")
    await engine.workflows.run_instance(
        instance.id,
        dispatch=engine.dispatch,
        notify=engine.notify,
    )
    return instance.model_dump(mode="json")


@app.get("/workflows/{workflow_id}/instances")
async def list_workflow_instances(
    workflow_id: str,
    engine: Annotated[AgencyEngine, Depends(get_engine)],
    limit: int = Query(50, ge=1, le=200),
) -> list[dict[str, Any]]:
    """List instances of a workflow."""
    return [i.model_dump(mode="json") for i in engine.workflows.list_instances(workflow_id, limit=limit)]


@app.get("/workflow-instances/{instance_id}")
async def get_workflow_instance(
    instance_id: str,
    engine: Annotated[AgencyEngine, Depends(get_engine)],
) -> dict[str, Any]:
    """Get a workflow instance by id."""
    instance = engine.workflows.get_instance(instance_id)
    if instance is None:
        raise HTTPException(status_code=404, detail="Workflow instance not found")
    return instance.model_dump(mode="json")


@app.post("/workflow-instances/{instance_id}/resume")
async def resume_workflow_instance(
    instance_id: str,
    engine: Annotated[AgencyEngine, Depends(get_engine)],
) -> dict[str, Any]:
    """Resume a paused workflow instance."""
    instance = await engine.workflows.resume_instance(
        instance_id,
        dispatch=engine.dispatch,
        notify=engine.notify,
    )
    if instance is None:
        raise HTTPException(status_code=404, detail="Workflow instance not found or not paused")
    return instance.model_dump(mode="json")


# ---------- Notifications ----------


class NotificationRequest(BaseModel):
    channel: str = "sse"
    title: str
    body: str
    recipient: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


@app.get("/notifications")
async def list_notifications(
    engine: Annotated[AgencyEngine, Depends(get_engine)],
    channel: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
) -> list[dict[str, Any]]:
    """List recent notifications."""
    ch = NotificationChannel(channel) if channel else None
    return [n.model_dump(mode="json") for n in engine.notifications.history(channel=ch, limit=limit)]


@app.post("/notifications")
async def send_notification(
    request: NotificationRequest,
    engine: Annotated[AgencyEngine, Depends(get_engine)],
) -> dict[str, Any]:
    """Send a notification through a specific channel."""
    try:
        channel = NotificationChannel(request.channel)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown channel: {request.channel}") from None
    notification = await engine.notify(
        channel,
        request.title,
        request.body,
        request.recipient,
        request.payload,
    )
    return notification.model_dump(mode="json")


@app.get("/notifications/stream")
async def notifications_stream(
    engine: Annotated[AgencyEngine, Depends(get_engine)],
) -> StreamingResponse:
    """Server-sent events stream for real-time dashboard notifications."""
    queue: asyncio.Queue[str] = asyncio.Queue()

    def listener(notification: Any) -> None:
        try:
            data = json.dumps(notification.model_dump(mode="json"))
            queue.put_nowait(f"data: {data}\n\n")
        except Exception:  # noqa: BLE001
            pass

    engine.notifications.subscribe(listener)

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield event
                except TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            engine.notifications.unsubscribe(listener)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# ---------- Webhooks ----------


@app.post("/webhooks/{source}")
async def ingest_webhook(
    source: str,
    request: Request,
    engine: Annotated[AgencyEngine, Depends(get_engine)],
) -> dict[str, Any]:
    """Ingest an external webhook and optionally trigger a workflow."""
    from sahiixx_agency.core.models import WebhookPayload

    try:
        payload = await request.json()
    except Exception:  # noqa: BLE001
        payload = {}

    webhook = WebhookPayload(source=source, event=request.headers.get("x-event", "unknown"), payload=payload)
    engine.memory.log_event("webhook.received", webhook.model_dump(mode="json"))
    engine.metrics.increment("webhooks_received_total", labels={"source": source})

    # Trigger event-based workflows that match this source/topic.
    triggered: list[str] = []
    for definition in engine.workflows.list_definitions():
        if definition.trigger == "event" and definition.event_topic == f"webhook.{source}":
            instance = engine.workflows.create_instance(definition.id, payload)
            if instance:
                await engine.workflows.run_instance(instance.id, dispatch=engine.dispatch, notify=engine.notify)
                triggered.append(instance.id)

    return {"source": source, "received": True, "triggered_instances": triggered}


# ---------- Chat ----------


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None
    title: str | None = None


class ChatResponse(BaseModel):
    thread_id: str
    response: str
    task_id: str
    messages: list[dict[str, Any]]


@app.post("/chat", response_model=ChatResponse)
async def create_chat_message(
    request: ChatRequest,
    engine: Annotated[AgencyEngine, Depends(get_engine)],
) -> dict[str, Any]:
    """Send a message to the agency command center.

    The message is dispatched as a task and stored in a chat thread for history.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    thread, agency_message, task = await engine.chat_message(
        thread_id=request.thread_id,
        content=request.message.strip(),
        title=request.title,
    )
    return {
        "thread_id": thread.id,
        "response": agency_message.content,
        "task_id": task.id,
        "messages": [m.model_dump(mode="json") for m in thread.messages],
    }


@app.get("/chat/{thread_id}")
async def get_chat_thread(
    thread_id: str,
    engine: Annotated[AgencyEngine, Depends(get_engine)],
) -> dict[str, Any]:
    """Retrieve the full message history for a chat thread."""
    thread = engine.get_chat_thread(thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread.model_dump(mode="json")


@app.get("/chat")
async def list_chat_threads(
    engine: Annotated[AgencyEngine, Depends(get_engine)],
    limit: int = Query(50, ge=1, le=200),
) -> list[dict[str, Any]]:
    """List recent chat threads."""
    threads = engine.chat.list_threads(limit=limit)
    return [t.model_dump(mode="json") for t in threads]


# ---------- Memory ----------


@app.get("/memory")
async def list_memory(
    engine: Annotated[AgencyEngine, Depends(get_engine)],
    limit: int = Query(100, ge=1, le=500),
) -> list[dict[str, Any]]:
    """Return stored agency memory entries."""
    return engine.list_memory_keys(limit=limit)


@app.post("/memory/{key}")
async def set_memory(
    key: str,
    value: dict[str, Any],
    engine: Annotated[AgencyEngine, Depends(get_engine)],
) -> dict[str, Any]:
    """Set a value in agency memory."""
    engine.set_memory(key, value)
    return {"status": "ok", "key": key}


# ---------- LLM ----------


class LLMChatRequest(BaseModel):
    """Request body for /llm/chat."""

    messages: list[LLMMessage] = Field(..., min_length=1)
    provider: str | None = Field(default=None, description="LLM provider id")
    model: str | None = Field(default=None, description="Model id")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1)
    tenant_id: str | None = Field(default=None, description="Owning tenant for cost attribution")
    project_id: str | None = Field(default=None, description="Owning project for cost attribution")


@app.get("/llm/providers")
async def list_llm_providers(engine: Annotated[AgencyEngine, Depends(get_engine)]) -> list[dict[str, Any]]:
    """List configured LLM providers and their readiness."""
    return engine.llm_manager.list_providers()


@app.post("/llm/chat")
async def llm_chat(
    request: LLMChatRequest,
    engine: Annotated[AgencyEngine, Depends(get_engine)],
) -> dict[str, Any]:
    """Send a chat request through a pluggable LLM provider and track cost."""
    import uuid

    task = AgencyTask(
        id=f"llm_chat_{uuid.uuid4().hex[:12]}",
        intent="Ad-hoc LLM chat",
        tenant_id=request.tenant_id,
        project_id=request.project_id,
    )
    try:
        response = await engine.llm_manager.chat(
            messages=request.messages,
            provider=request.provider,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            task=task,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Provider request failed: {exc}") from exc
    return response.model_dump(mode="json")


@app.get("/llm/costs")
async def llm_costs(
    engine: Annotated[AgencyEngine, Depends(get_engine)],
    provider: str | None = Query(None),
    model: str | None = Query(None),
    since: str | None = Query(None, description="ISO 8601 start time"),
    until: str | None = Query(None, description="ISO 8601 end time"),
) -> dict[str, Any]:
    """Return aggregated LLM usage and cost records."""
    from datetime import datetime as _dt

    since_dt = _dt.fromisoformat(since) if since else None
    until_dt = _dt.fromisoformat(until) if until else None
    return engine.llm_manager.cost_summary(provider=provider, model=model, since=since_dt, until=until_dt)


# ---------- Config ----------


@app.get("/config/white-label")
async def get_white_label_config(
    engine: Annotated[AgencyEngine, Depends(get_engine)],
    project_id: str | None = Query(None),
) -> dict[str, Any]:
    """Return white-label dashboard branding config for a project."""
    return engine.get_white_label_config(project_id)


# ---------- Costs ----------


@app.get("/costs")
async def list_costs(
    engine: Annotated[AgencyEngine, Depends(get_engine)],
    tenant_id: str | None = Query(None),
    project_id: str | None = Query(None),
    category: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1_000),
) -> list[dict[str, Any]]:
    """List cost records, optionally filtered by tenant, project, and category."""
    records = engine.cost_ledger.list_records(
        tenant_id=tenant_id,
        project_id=project_id,
        category=category,
        limit=limit,
    )
    return [r.model_dump(mode="json") for r in records]


@app.get("/costs/summary")
async def costs_summary(
    engine: Annotated[AgencyEngine, Depends(get_engine)],
    tenant_id: str | None = Query(None),
    project_id: str | None = Query(None),
) -> dict[str, Any]:
    """Return aggregated costs for the selected tenant/project."""
    return engine.cost_ledger.summary(tenant_id=tenant_id, project_id=project_id)


# ---------- Intel ----------


@app.get("/intel")
async def run_intel(
    engine: Annotated[AgencyEngine, Depends(get_engine)],
    report_type: str = Query("trending"),
    min_stars: int = Query(50, ge=0),
) -> dict[str, Any]:
    report = await engine.run_intel_scout(report_type, min_stars=min_stars)
    return report.model_dump(mode="json")


# ---------- Discovery ----------


class DiscoveryRunRequest(BaseModel):
    min_stars: int | None = None
    auto_clone: bool | None = None


@app.post("/discovery/run")
async def run_discovery(
    request: Annotated[DiscoveryRunRequest, Body(default_factory=DiscoveryRunRequest)],
    engine: Annotated[AgencyEngine, Depends(get_engine)],
) -> dict[str, Any]:
    """Run the discovery pipeline and return newly discovered repos."""
    from sahiixx_agency.discovery.pipeline import DiscoveryPipeline

    discovery_config = engine.config.discovery
    pipeline = DiscoveryPipeline(
        data_dir=engine.config.data_dir,
        min_stars=request.min_stars if request.min_stars is not None else discovery_config.min_stars,
        auto_clone=request.auto_clone if request.auto_clone is not None else discovery_config.auto_clone,
    )
    nodes = await pipeline.run()
    return {"discovered": len(nodes), "repos": [n.model_dump(mode="json") for n in nodes[:50]]}


@app.get("/discovery/trending")
async def list_trending(engine: Annotated[AgencyEngine, Depends(get_engine)]) -> list[dict[str, Any]]:
    """Return the most recent daily snapshot of discovered repos."""
    from datetime import datetime, timezone
    from pathlib import Path

    from sahiixx_agency.core.models import DiscoveryResult

    data_dir = Path(engine.config.data_dir) / "discovery"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = data_dir / f"{today}.jsonl"
    if not path.exists():
        return []
    results = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(DiscoveryResult.model_validate_json(line).model_dump(mode="json"))
    return results


@app.get("/discovery/snapshots")
async def list_snapshots(engine: Annotated[AgencyEngine, Depends(get_engine)]) -> list[dict[str, Any]]:
    """List available discovery snapshot files."""
    from pathlib import Path

    data_dir = Path(engine.config.data_dir) / "discovery"
    snapshots: list[dict[str, Any]] = []
    if data_dir.exists():
        for path in sorted(data_dir.glob("*.jsonl")):
            snapshots.append({"date": path.stem, "filename": path.name, "path": str(path)})
    return snapshots


# ---------- Telegram ----------


@app.get("/telegram/status")
async def telegram_status(engine: Annotated[AgencyEngine, Depends(get_engine)]) -> dict[str, Any]:
    """Return Telegram bot configuration status."""
    cfg = engine.config.telegram
    return {
        "enabled": cfg.enabled,
        "has_token": bool(cfg.token or os.environ.get("TELEGRAM_BOT_TOKEN")),
        "webhook_url": cfg.webhook_url,
        "allowed_chat_ids_count": len(cfg.allowed_chat_ids),
    }


@app.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    engine: Annotated[AgencyEngine, Depends(get_engine)],
) -> dict[str, str]:
    """Receive Telegram updates via webhook and process them."""
    token = engine.config.telegram.token or os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise HTTPException(status_code=400, detail="Telegram bot token not configured")

    from sahiixx_agency.telegram.bot import AgencyTelegramBot

    bot = AgencyTelegramBot(token=token, engine=engine, config=engine.config)
    application = bot._build_app()
    application.bot_data["bot"] = bot

    from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler, filters

    application.add_handler(CommandHandler("start", bot._cmd_start))
    application.add_handler(CommandHandler("help", bot._cmd_help))
    application.add_handler(CommandHandler("dispatch", bot._cmd_dispatch))
    application.add_handler(CommandHandler("tasks", bot._cmd_tasks))
    application.add_handler(CommandHandler("task", bot._cmd_task))
    application.add_handler(CommandHandler("approve", bot._cmd_approve))
    application.add_handler(CommandHandler("reject", bot._cmd_reject))
    application.add_handler(CommandHandler("approvals", bot._cmd_approvals))
    application.add_handler(CommandHandler("stats", bot._cmd_stats))
    application.add_handler(CommandHandler("registry", bot._cmd_registry))
    application.add_handler(CallbackQueryHandler(bot._callback_approve, pattern=r"^approve:"))
    application.add_handler(CallbackQueryHandler(bot._callback_reject, pattern=r"^reject:"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot._handle_text))

    body = await request.json()
    await application.process_update(body)
    return {"status": "ok"}


@app.get("/dashboard/graph-data")
async def graph_data(engine: Annotated[AgencyEngine, Depends(get_engine)]) -> dict[str, Any]:
    """Serve graph data for the React dashboard."""
    nodes = []
    links = []
    categories = set()
    layers = set()
    eras = set()

    for mod in engine.registry.modules:
        cat = mod.category.value.replace("_", " ").title()
        categories.add(cat)
        layers.add(mod.language or "Unknown")
        eras.add("recent" if mod.updated_at and (mod.updated_at.year >= 2025) else "landmark")
        nodes.append(
            {
                "id": mod.id,
                "name": mod.name,
                "stars": mod.stars,
                "category": cat,
                "layer": mod.language or "Unknown",
                "era": "recent" if mod.updated_at and (mod.updated_at.year >= 2025) else "landmark",
                "url": mod.url,
                "description": mod.description or "",
                "language": mod.language or "N/A",
                "why": " | ".join(mod.capabilities) or "Agency module",
            }
        )

    # Simple linking by shared language
    by_lang: dict[str, list[str]] = {}
    for mod in engine.registry.modules:
        lang = mod.language or "Unknown"
        by_lang.setdefault(lang, []).append(mod.id)

    for _lang, ids in by_lang.items():
        for i in range(len(ids)):
            for j in range(i + 1, min(i + 3, len(ids))):
                links.append(
                    {
                        "source": ids[i],
                        "target": ids[j],
                        "type": "related",
                        "strength": 0.5,
                    }
                )

    return {
        "nodes": nodes,
        "links": links,
        "categories": sorted(categories),
        "layers": sorted(layers),
        "eras": sorted(eras),
        "stats": {
            "totalRepos": len(nodes),
            "totalStars": sum(m.stars for m in engine.registry.modules),
            "totalForks": sum(m.forks for m in engine.registry.modules),
            "totalLanguages": len(layers),
        },
    }


# Static dashboard files
static_dir = os.path.join(os.path.dirname(__file__), "../../dashboard/dist")
if os.path.exists(static_dir):
    # Serve built JS/CSS assets at /dashboard/assets (matches Vite's relative output)
    app.mount("/dashboard/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="dashboard-assets")

    @app.get("/dashboard")
    async def dashboard_index() -> RedirectResponse:
        # Redirect to trailing slash so relative asset paths resolve correctly.
        return RedirectResponse(url="/dashboard/")

    @app.get("/dashboard/{path:path}")
    async def dashboard_spa(path: str) -> FileResponse:
        return FileResponse(os.path.join(static_dir, "index.html"))
else:

    @app.get("/dashboard")
    async def dashboard_not_built() -> dict[str, str]:
        return {"status": "Dashboard not built. Run 'cd dashboard && npm run build'"}
