"""Tests for the GCC Outbound skills API endpoints."""

from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient

from sahiixx_agency.api.main import app, get_engine
from sahiixx_agency.core.engine import AgencyEngine
from sahiixx_agency.core.models import AgencyConfig


@pytest.fixture
def client(tmp_path, monkeypatch):
    config = AgencyConfig(data_dir=str(tmp_path))
    engine = AgencyEngine(config)

    @asynccontextmanager
    async def _noop_lifespan(_app):
        yield

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


def test_list_skills(client):
    response = client.get("/api/skills")
    assert response.status_code == 200
    data = response.json()
    assert "skills" in data
    assert len(data["skills"]) >= 1

    ids = [s["id"] for s in data["skills"]]
    assert "gcc-outbound-prospecting" in ids

    skill = next(s for s in data["skills"] if s["id"] == "gcc-outbound-prospecting")
    assert skill["name"] == "gcc-outbound-prospecting"
    assert "description" in skill
    assert "tags" in skill
    assert "version" in skill


def test_run_skill_success(client):
    payload = {
        "prospect": {
            "name": "Ahmed",
            "company": "NoorTech",
            "role": "CTO",
            "country": "AE",
        },
        "our_company": {"name": "Sahiix", "value_prop": "AI agents for GCC"},
        "signal": {"type": "hiring", "description": "Hiring 5 AI engineers"},
    }
    response = client.post("/api/skills/gcc-outbound-prospecting/run", json={"payload": payload})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["task_id"] is None
    assert "result" in data
    assert data["result"]["skill"] == "gcc_outbound_prospecting"
    assert "subject" in data["result"]
    assert "body" in data["result"]


def test_run_skill_async_returns_task_id(client):
    payload = {
        "prospect": {"name": "Ahmed", "company": "NoorTech", "role": "CTO", "country": "AE"},
        "our_company": {"name": "Sahiix", "value_prop": "AI agents"},
        "signal": {"description": "Hiring"},
    }
    response = client.post(
        "/api/skills/gcc-outbound-prospecting/run",
        json={"payload": payload, "async": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["task_id"] is not None
    assert data["task_id"].startswith("task_")


def test_run_skill_missing_required_fields(client):
    response = client.post(
        "/api/skills/gcc-outbound-prospecting/run",
        json={"payload": {"prospect": {}, "signal": {}}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "result" in data


def test_run_skill_not_found(client):
    response = client.post("/api/skills/nonexistent-skill/run", json={"payload": {}})
    assert response.status_code == 404
    assert "Skill not found" in response.json()["detail"]


def test_run_skill_with_lead_scoring(client):
    payload = {
        "leads": [
            {"name": "A", "company": "X", "role": "CTO", "country": "AE", "signal": "hiring"},
        ],
        "icp": {"target_roles": ["CTO"], "target_countries": ["AE"]},
    }
    response = client.post("/api/skills/gcc-lead-scoring/run", json={"payload": payload})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "scored_leads" in data["result"]
    assert data["result"]["skill"] == "gcc_lead_scoring"
