"""Tests for the FastAPI server."""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient

from sahiixx_agency.api.main import app, get_engine
from sahiixx_agency.core.engine import AgencyEngine
from sahiixx_agency.core.models import AgencyConfig, RepoCategory, RepoNode, TaskStatus

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
def client(tmp_path, monkeypatch):
    config = AgencyConfig(data_dir=str(tmp_path))
    engine = AgencyEngine(config)

    async def fake_discover(username: str) -> list[RepoNode]:
        for module in FAKE_MODULES:
            engine.registry._modules[module.id] = module
        return FAKE_MODULES

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

    async def _setup() -> None:
        await engine.sync_repos("sahiixx")

    @asynccontextmanager
    async def _noop_lifespan(_app):
        yield

    asyncio.run(_setup())
    app.dependency_overrides[get_engine] = lambda: engine
    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = _noop_lifespan
    try:
        with TestClient(app) as test_client:
            test_client.portal.call(engine.start_worker)
            yield test_client
            test_client.portal.call(engine.stop_worker)
    finally:
        app.dependency_overrides.clear()
        app.router.lifespan_context = original_lifespan


def test_create_task_returns_pending(client):
    response = client.post("/tasks", params={"intent": "run voice assistant"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending"
    assert data["id"].startswith("task_")


def test_get_task_status_flow(client):
    create = client.post("/tasks", params={"intent": "run voice assistant"})
    task_id = create.json()["id"]

    status = "pending"
    for _ in range(20):
        resp = client.get(f"/tasks/{task_id}")
        status = resp.json()["status"]
        if status in ("completed", "failed"):
            break
        time.sleep(0.05)

    assert status in ("completed", "failed")


def test_get_task_not_found(client):
    resp = client.get("/tasks/task_does_not_exist")
    assert resp.status_code == 404


def test_approve_task_endpoint(client):
    create = client.post(
        "/dispatch",
        json={"intent": "run voice assistant", "payload": {"risk_level": "critical"}},
    )
    assert create.status_code == 200
    task_id = create.json()["id"]

    approve = client.post(f"/tasks/{task_id}/approve")
    assert approve.status_code == 200
    assert approve.json()["status"] == "approved"

    status = "pending"
    for _ in range(20):
        resp = client.get(f"/tasks/{task_id}")
        status = resp.json()["status"]
        if status in ("completed", "failed"):
            break
        time.sleep(0.05)

    assert status == "completed"


def test_approve_task_not_found(client):
    resp = client.post("/tasks/task_does_not_exist/approve")
    assert resp.status_code == 404


def test_approve_task_no_request(client):
    create = client.post("/tasks", params={"intent": "run voice assistant"})
    assert create.status_code == 200
    task_id = create.json()["id"]

    resp = client.post(f"/tasks/{task_id}/approve")
    assert resp.status_code == 400
    assert "No approval request" in resp.json()["detail"]


def test_chat_endpoint_creates_thread(client):
    response = client.post("/chat", json={"message": "run voice assistant"})
    assert response.status_code == 200
    data = response.json()
    assert data["thread_id"].startswith("thread_")
    assert "task_id" in data
    assert data["response"]
    messages = data["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "agency"


def test_get_chat_thread(client):
    create = client.post("/chat", json={"message": "hello agency"})
    assert create.status_code == 200
    thread_id = create.json()["thread_id"]

    response = client.get(f"/chat/{thread_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == thread_id
    assert len(data["messages"]) >= 2
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][1]["role"] == "agency"


def test_list_pending_approvals_and_approve(client):
    create = client.post(
        "/dispatch",
        json={"intent": "run voice assistant", "payload": {"risk_level": "critical"}},
    )
    assert create.status_code == 200
    task_id = create.json()["id"]

    for _ in range(20):
        task = client.get(f"/tasks/{task_id}").json()
        if task["status"] == "pending":
            break
        time.sleep(0.05)

    pending = client.get("/approvals/pending")
    assert pending.status_code == 200
    reqs = pending.json()
    assert len(reqs) >= 1
    req = next((r for r in reqs if r["task_id"] == task_id), None)
    assert req is not None

    approve = client.post(f"/approvals/{req['id']}/approve")
    assert approve.status_code == 200
    assert approve.json()["status"] == "approved"

    status = "pending"
    for _ in range(20):
        resp = client.get(f"/tasks/{task_id}")
        status = resp.json()["status"]
        if status in ("completed", "failed"):
            break
        time.sleep(0.05)
    assert status == "completed"


def test_reject_approval(client):
    create = client.post(
        "/dispatch",
        json={"intent": "run voice assistant", "payload": {"risk_level": "high"}},
    )
    assert create.status_code == 200
    task_id = create.json()["id"]

    for _ in range(20):
        task = client.get(f"/tasks/{task_id}").json()
        if task["status"] == "pending":
            break
        time.sleep(0.05)

    reqs = client.get("/approvals/pending").json()
    req = next((r for r in reqs if r["task_id"] == task_id), None)
    assert req is not None

    reject = client.post(f"/approvals/{req['id']}/reject")
    assert reject.status_code == 200
    assert reject.json()["status"] == "rejected"

    task = client.get(f"/tasks/{task_id}").json()
    assert task["status"] == "cancelled"


def test_memory_endpoint(client):
    response = client.get("/memory")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_telegram_status_endpoint(client):
    response = client.get("/telegram/status")
    assert response.status_code == 200
    data = response.json()
    assert "enabled" in data
    assert "has_token" in data


def test_telegram_webhook_without_token(client):
    response = client.post("/telegram/webhook", json={"update_id": 1})
    assert response.status_code == 400


# ---------- Chat & Memory & Approval Queue ----------


def test_chat_creates_thread_and_task(client):
    response = client.post("/chat", json={"message": "run voice assistant"})
    assert response.status_code == 200
    data = response.json()
    assert data["thread_id"].startswith("thread_")
    assert data["task_id"].startswith("task_")
    assert "run voice assistant" in [m["content"] for m in data["messages"]]
    assert any(m["role"] == "agency" for m in data["messages"])


def test_chat_requires_message(client):
    response = client.post("/chat", json={"message": "   "})
    assert response.status_code == 400


def test_chat_thread_history(client):
    create = client.post("/chat", json={"message": "run voice assistant"})
    thread_id = create.json()["thread_id"]

    response = client.get(f"/chat/{thread_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == thread_id
    assert len(data["messages"]) >= 2


def test_chat_thread_not_found(client):
    response = client.get("/chat/thread_does_not_exist")
    assert response.status_code == 404


def test_chat_agent_mode_dispatches_planned_intent(client, monkeypatch):
    async def fake_llm_chat(*args, **kwargs):
        from sahiixx_agency.core.models import LLMResponse

        return LLMResponse(provider="test", model="test", content="INTENT: run voice assistant")

    monkeypatch.setattr("sahiixx_agency.api.main.get_engine", lambda: client.app.dependency_overrides.get(get_engine, lambda: None)())
    # The TestClient holds the overridden engine via dependency_overrides.
    engine = client.app.dependency_overrides[get_engine]()
    monkeypatch.setattr(engine, "llm_chat", fake_llm_chat)

    response = client.post("/chat", json={"message": "I want a voice assistant", "agent": True})
    assert response.status_code == 200
    data = response.json()
    assert data["thread_id"].startswith("thread_")
    assert data["task_id"].startswith("task_")
    assert any("Agent dispatched task" in m["content"] for m in data["messages"] if m["role"] == "agency")


def test_list_tasks_includes_module_alias(client):
    client.post("/tasks", params={"intent": "run voice assistant"})
    response = client.get("/tasks")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert "module" in data[0]
    assert "module_id" in data[0]


def test_approval_queue_pending(client):
    # Create a high-risk task to generate an approval request.
    create = client.post(
        "/dispatch",
        json={"intent": "run voice assistant", "payload": {"risk_level": "critical"}},
    )
    task_id = create.json()["id"]

    response = client.get("/approvals/pending")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(a["task_id"] == task_id for a in data)


def test_approve_by_approval_id(client):
    create = client.post(
        "/dispatch",
        json={"intent": "run voice assistant", "payload": {"risk_level": "critical"}},
    )
    task_id = create.json()["id"]

    pending = client.get("/approvals/pending").json()
    approval_id = next(a["id"] for a in pending if a["task_id"] == task_id)

    response = client.post(f"/approvals/{approval_id}/approve")
    assert response.status_code == 200
    assert response.json()["status"] == "approved"

    status = "pending"
    for _ in range(20):
        resp = client.get(f"/tasks/{task_id}")
        status = resp.json()["status"]
        if status in ("completed", "failed"):
            break
        time.sleep(0.05)
    assert status == "completed"


def test_reject_by_approval_id(client):
    create = client.post(
        "/dispatch",
        json={"intent": "run voice assistant", "payload": {"risk_level": "high"}},
    )
    task_id = create.json()["id"]

    pending = client.get("/approvals/pending").json()
    approval_id = next(a["id"] for a in pending if a["task_id"] == task_id)

    response = client.post(f"/approvals/{approval_id}/reject")
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"

    task = client.get(f"/tasks/{task_id}").json()
    assert task["status"] == "cancelled"


def test_approve_by_id_not_found(client):
    response = client.post("/approvals/apr_does_not_exist/approve")
    assert response.status_code == 404


def test_list_approvals_filtered(client):
    client.post(
        "/dispatch",
        json={"intent": "run voice assistant", "payload": {"risk_level": "critical"}},
    )
    response = client.get("/approvals?status=pending")
    assert response.status_code == 200
    data = response.json()
    assert all(a["status"] == "pending" for a in data)


def test_memory_endpoints(client):
    set_resp = client.post("/memory/test-key", json={"value": 42})
    assert set_resp.status_code == 200

    list_resp = client.get("/memory")
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert any(entry["key"] == "test-key" for entry in data)


def test_health_endpoint_returns_checks(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "checks" in data
    assert data["registry_count"] == 2


def test_metrics_endpoint(client):
    client.post("/tasks", params={"intent": "run voice assistant"})
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "opa_" in response.text


def test_workflow_crud(client):
    workflow = {
        "id": "test-wf",
        "name": "Test Workflow",
        "trigger": "manual",
        "steps": [
            {"id": "s1", "name": "Step 1", "action": "notify", "payload": {"channel": "sse", "title": "Hi", "body": "Hello"}},
        ],
    }
    create = client.post("/workflows", json=workflow)
    assert create.status_code == 200

    get = client.get("/workflows/test-wf")
    assert get.status_code == 200
    assert get.json()["name"] == "Test Workflow"

    list_resp = client.get("/workflows")
    assert list_resp.status_code == 200
    assert any(w["id"] == "test-wf" for w in list_resp.json())

    run = client.post("/workflows/test-wf/run", json={"context": {}})
    assert run.status_code == 200
    assert run.json()["status"] == "completed"

    delete = client.delete("/workflows/test-wf")
    assert delete.status_code == 200


def test_workflow_from_natural_language(client, monkeypatch):
    async def fake_llm_chat(*args, **kwargs):
        from sahiixx_agency.core.models import LLMResponse, LLMUsage

        return LLMResponse(
            provider="test",
            model="test",
            content='{"id":"nl-wf","name":"NL Workflow","trigger":"manual","steps":[{"id":"step_1","name":"Notify","action":"notify","payload":{"channel":"sse","title":"Hi","body":"Hello"}}],"enabled":true}',
            usage=LLMUsage(input_tokens=100, output_tokens=50, total_tokens=150),
        )

    engine = client.app.dependency_overrides[get_engine]()
    monkeypatch.setattr(engine, "llm_chat", fake_llm_chat)

    response = client.post("/workflows/from-natural-language", json={"description": "Create a workflow that sends a hello notification"})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "nl-wf"
    assert data["name"] == "NL Workflow"
    assert any(step["id"] == "step_1" for step in data["steps"])


def test_workflow_webhook_trigger_endpoint(client):
    workflow = {
        "id": "webhook-test-wf",
        "name": "Webhook Test",
        "trigger": "webhook",
        "steps": [
            {"id": "s1", "name": "Process", "action": "notify", "payload": {"channel": "sse", "title": "Webhook", "body": "Received"}},
        ],
    }
    assert client.post("/workflows", json=workflow).status_code == 200

    response = client.post("/workflows/webhook-test-wf/trigger", json={"action": "push"})
    assert response.status_code == 200
    data = response.json()
    assert data["workflow_id"] == "webhook-test-wf"
    assert data["status"] == "completed"


def test_workflow_webhook_trigger_rejects_non_webhook_workflow(client):
    workflow = {
        "id": "manual-test-wf",
        "name": "Manual Test",
        "trigger": "manual",
        "steps": [{"id": "s1", "name": "Step", "action": "noop"}],
    }
    assert client.post("/workflows", json=workflow).status_code == 200

    response = client.post("/workflows/manual-test-wf/trigger", json={})
    assert response.status_code == 400
    assert "not configured for webhook" in response.json()["detail"]


def test_notification_send(client):
    response = client.post("/notifications", json={"channel": "sse", "title": "Test", "body": "Hello"})
    assert response.status_code == 200
    data = response.json()
    assert data["channel"] == "sse"
    assert data["status"] == "sent"


def test_webhook_ingest(client):
    response = client.post("/webhooks/github", json={"action": "push"}, headers={"x-event": "push"})
    assert response.status_code == 200
    assert response.json()["received"] is True


def test_api_prefix_middleware(client):
    """Requests to /api/* are rewritten to /* before routing."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_dashboard_redirect(client):
    """/dashboard redirects to /dashboard/ so relative assets resolve."""
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/dashboard/"


def test_dashboard_assets_served(client):
    """Built JS assets are served from /dashboard/assets."""
    import glob
    import os

    static_dir = os.path.join(os.path.dirname(__file__), "..", "dashboard", "dist", "assets")
    js_files = glob.glob(os.path.join(static_dir, "*.js"))
    assert js_files, "No built JS assets found"
    asset_name = os.path.basename(js_files[0])
    response = client.get(f"/dashboard/assets/{asset_name}")
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]


def test_execute_module_runs_through_task_lifecycle(client, monkeypatch):
    """Direct module execution must create a task and run through the engine lifecycle."""
    executed: list[tuple[str, dict]] = []

    async def fake_execute_task(self, task):
        executed.append((task.module_id, task.payload))
        task.status = TaskStatus.COMPLETED
        task.result = {"status": "success"}

    monkeypatch.setattr("sahiixx_agency.core.engine.AgencyEngine._execute_task", fake_execute_task)

    response = client.post("/tasks/echo-module/execute")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["task_id"].startswith("task_")
    assert data["module"] == "echo-module"


def test_execute_module_respects_dependency_scan(client, monkeypatch):
    """Direct module execution must fail when the dependency scan gate fails."""
    from sahiixx_agency.core.dependency_scanner import DependencyScanner

    async def failing_scan(self, node):
        from sahiixx_agency.core.models import DependencyScanReport

        return DependencyScanReport(
            passed=False,
            failures=["CVE-2023-0001"],
            command="scan",
            stderr="vulnerable",
        )

    monkeypatch.setattr(DependencyScanner, "scan", failing_scan)

    engine = client.app.dependency_overrides[get_engine]()
    engine.config.security.dependency_scan_enabled = True

    response = client.post("/tasks/echo-module/execute")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert "dependency_scan" in (data["result"] or {})


# ---------- White-Label Config ----------


def test_white_label_config_defaults(client):
    """White-label endpoint returns default One Person Agency branding."""
    response = client.get("/config/white-label")
    assert response.status_code == 200
    data = response.json()
    assert data["brandName"] == "One Person Agency"
    assert data["logoUrl"] == ""
    assert data["primaryColor"] == "#6366f1"
    assert data["faviconUrl"] == ""


def test_white_label_config_per_project(client):
    """White-label endpoint returns a stored project config or defaults."""
    config = {
        "brandName": "Acme Corp",
        "logoUrl": "https://example.com/logo.png",
        "primaryColor": "#ef4444",
        "faviconUrl": "https://example.com/favicon.ico",
    }
    set_resp = client.post("/memory/project:acme:white_label", json=config)
    assert set_resp.status_code == 200

    response = client.get("/config/white-label?project_id=acme")
    assert response.status_code == 200
    data = response.json()
    assert data["brandName"] == "Acme Corp"
    assert data["logoUrl"] == "https://example.com/logo.png"
    assert data["primaryColor"] == "#ef4444"
    assert data["faviconUrl"] == "https://example.com/favicon.ico"

    # Unknown project falls back to defaults.
    response = client.get("/config/white-label?project_id=unknown")
    assert response.status_code == 200
    data = response.json()
    assert data["brandName"] == "One Person Agency"
    assert data["primaryColor"] == "#6366f1"
