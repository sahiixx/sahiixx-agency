"""Tests for the FastAPI server."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from sahiixx_agency.api.main import app, get_engine
from sahiixx_agency.core.engine import AgencyEngine
from sahiixx_agency.core.models import AgencyConfig, RepoCategory, RepoNode

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
        engine.registry._save()
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

    # Ensure the lifespan and endpoints use this engine instance.
    monkeypatch.setattr("sahiixx_agency.api.main.AgencyEngine", lambda config: engine)
    app.dependency_overrides[get_engine] = lambda: engine
    with TestClient(app) as test_client:
        yield test_client
        app.dependency_overrides.clear()


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
    for _ in range(40):
        resp = client.get(f"/tasks/{task_id}")
        status = resp.json()["status"]
        if status in ("completed", "failed"):
            break
        time.sleep(0.25)

    assert status in ("completed", "failed")


def test_get_task_not_found(client):
    resp = client.get("/tasks/task_does_not_exist")
    assert resp.status_code == 404
