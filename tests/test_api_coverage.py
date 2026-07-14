"""Additional API tests for uncovered endpoints.

These fill gaps in the main test_api.py coverage for endpoints that were
not exercised: root, stats, registry CRUD, task logs, workflow instances,
LLM, discovery, marketplace, and costs.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from sahiixx_agency.api.main import app, get_engine
from sahiixx_agency.core.engine import AgencyEngine
from sahiixx_agency.core.models import AgencyConfig


@pytest.fixture
def client(tmp_path, monkeypatch):
    config = AgencyConfig(data_dir=str(tmp_path))
    engine = AgencyEngine(config)

    async def fake_discover(username: str):
        from sahiixx_agency.core.models import RepoCategory, RepoNode

        module = RepoNode(
            id="echo-module",
            name="echo-module",
            full_name="sahiixx/echo-module",
            url="https://github.com/sahiixx/echo-module",
            category=RepoCategory.AGENT_FRAMEWORK,
            language="python",
            stars=10,
            capabilities=["echo"],
        )
        engine.registry._modules[module.id] = module
        return [module]

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

    async def _setup():
        await engine.sync_repos("sahiixx")

    import asyncio

    asyncio.run(_setup())
    app.dependency_overrides[get_engine] = lambda: engine

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _noop_lifespan(_app):
        yield

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


# ─── Root & Status ───────────────────────────────────────────────────────────


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "One Person Agency"
    assert data["status"] == "running"


def test_stats_endpoint(client):
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert "registry" in data
    assert data["registry"]["total_modules"] >= 1


# ─── Registry ────────────────────────────────────────────────────────────────


def test_list_registry(client):
    response = client.get("/registry")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["id"] == "echo-module"


def test_get_registry_module(client):
    response = client.get("/registry/echo-module")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "echo-module"
    assert data["name"] == "echo-module"


def test_get_registry_module_not_found(client):
    response = client.get("/registry/does-not-exist")
    assert response.status_code == 404


def test_registry_sync_endpoint(client):
    response = client.post("/registry/sync")
    assert response.status_code == 200
    data = response.json()
    assert "synced" in data
    assert data["username"] == "sahiixx"


# ─── Tasks ───────────────────────────────────────────────────────────────────


def test_list_tasks(client):
    client.post("/tasks", params={"intent": "run voice assistant"})
    response = client.get("/tasks")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_get_task_logs_empty(client):
    create = client.post("/tasks", params={"intent": "run voice assistant"})
    task_id = create.json()["id"]
    response = client.get(f"/tasks/{task_id}/logs")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_reject_task_endpoint(client):
    create = client.post(
        "/dispatch",
        json={"intent": "run voice assistant", "payload": {"risk_level": "high"}},
    )
    task_id = create.json()["id"]
    response = client.post(f"/tasks/{task_id}/reject")
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


# ─── Approvals ───────────────────────────────────────────────────────────────


def test_list_approvals(client):
    client.post(
        "/dispatch",
        json={"intent": "run voice assistant", "payload": {"risk_level": "critical"}},
    )
    response = client.get("/approvals")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


# ─── Workflows ───────────────────────────────────────────────────────────────


def test_get_workflow(client):
    workflow = {
        "id": "test-wf-get",
        "name": "Test Get",
        "trigger": "manual",
        "steps": [{"id": "s1", "name": "Step", "action": "noop", "payload": {}}],
    }
    client.post("/workflows", json=workflow)
    response = client.get("/workflows/test-wf-get")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Get"


def test_list_workflow_instances(client):
    workflow = {
        "id": "test-wf-instances",
        "name": "Test Instances",
        "trigger": "manual",
        "steps": [{"id": "s1", "name": "Step", "action": "noop", "payload": {}}],
    }
    client.post("/workflows", json=workflow)
    client.post("/workflows/test-wf-instances/run", json={"context": {}})
    response = client.get("/workflows/test-wf-instances/instances")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_workflow_instance(client):
    workflow = {
        "id": "test-wf-instance-get",
        "name": "Test Instance Get",
        "trigger": "manual",
        "steps": [{"id": "s1", "name": "Step", "action": "noop", "payload": {}}],
    }
    client.post("/workflows", json=workflow)
    run = client.post("/workflows/test-wf-instance-get/run", json={"context": {}})
    instance_id = run.json()["id"]
    response = client.get(f"/workflow-instances/{instance_id}")
    assert response.status_code == 200
    assert response.json()["id"] == instance_id


# ─── LLM ─────────────────────────────────────────────────────────────────────


def test_list_llm_providers(client):
    response = client.get("/llm/providers")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_llm_costs_endpoint(client):
    response = client.get("/llm/costs")
    assert response.status_code == 200


# ─── Discovery ─────────────────────────────────────────────────────────────────


def test_discovery_trending_empty(client):
    response = client.get("/discovery/trending")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_discovery_snapshots_empty(client):
    response = client.get("/discovery/snapshots")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


# ─── Marketplace ───────────────────────────────────────────────────────────────


def test_list_marketplace(client):
    response = client.get("/marketplace")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_marketplace_module(client):
    response = client.get("/marketplace/echo-module")
    assert response.status_code == 200


# ─── Costs ─────────────────────────────────────────────────────────────────────


def test_list_costs(client):
    response = client.get("/costs")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_costs_summary(client):
    response = client.get("/costs/summary")
    assert response.status_code == 200


# ─── Intel ───────────────────────────────────────────────────────────────────────


def test_intel_endpoint(client):
    response = client.get("/intel")
    assert response.status_code == 200
    data = response.json()
    assert "report_type" in data or "modules" in data or "results" in data


# ─── Dashboard Graph Data ──────────────────────────────────────────────────────


def test_dashboard_graph_data(client):
    response = client.get("/dashboard/graph-data")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "links" in data
    assert "categories" in data
    assert "stats" in data
    assert data["stats"]["totalRepos"] >= 1


def test_dashboard_graph_data_includes_ecosystem_stubs(client):
    """Promoted ecosystem modules (from config) should appear as graph nodes."""
    from sahiixx_agency.api.main import app, get_engine

    engine = app.dependency_overrides[get_engine]()
    engine.config.ecosystem["trufflehog"] = {
        "repo": "trufflehog",
        "owner": "trufflesecurity",
        "url": "https://github.com/trufflesecurity/trufflehog",
        "role": "Find leaked credentials across codebases",
        "bus_channel": "security.*",
        "protocol": "subprocess",
        "priority": 2,
        "tags": ["security", "trufflehog"],
    }

    response = client.get("/dashboard/graph-data")
    assert response.status_code == 200
    data = response.json()
    ids = {n["id"] for n in data["nodes"]}
    assert "trufflehog" in ids
    promoted = [n for n in data["nodes"] if n.get("era") == "promoted"]
    assert promoted, "expected at least one 'promoted' era node"
    # Promoted nodes must carry the fields the dashboard expects.
    for n in promoted:
        assert {"id", "name", "category", "url", "description"} <= set(n)
    # Promoted stubs should be linked into the graph by category.
    linked = {link["source"] for link in data["links"]} | {link["target"] for link in data["links"]}
    promoted_ids = {n["id"] for n in promoted}
    assert promoted_ids & linked, "promoted nodes should be connected to the graph"
