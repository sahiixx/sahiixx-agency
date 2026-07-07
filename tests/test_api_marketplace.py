from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient

from sahiixx_agency.api.main import app, get_engine
from sahiixx_agency.core.engine import AgencyEngine
from sahiixx_agency.core.models import AgencyConfig, RepoCategory, RepoNode


@pytest.fixture
def client(tmp_path, monkeypatch):
    config = AgencyConfig(data_dir=str(tmp_path), memory_backend="json")
    engine = AgencyEngine(config)
    node = RepoNode(
        id="html-anything",
        name="html-anything",
        full_name="nexu-io/html-anything",
        url="https://github.com/nexu-io/html-anything",
        category=RepoCategory.COOKBOOK,
    )
    engine.registry._modules[node.id] = node
    engine.registry.save()

    @asynccontextmanager
    async def _noop_lifespan(_app):
        yield

    app.dependency_overrides[get_engine] = lambda: engine
    app.state.engine = engine
    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = _noop_lifespan
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        app.router.lifespan_context = original_lifespan


def test_list_marketplace(client):
    response = client.get("/marketplace")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["module"]["id"] == "html-anything"


def test_get_marketplace_module(client):
    response = client.get("/marketplace/html-anything")
    assert response.status_code == 200
    assert response.json()["module"]["id"] == "html-anything"


def test_install_module(client, tmp_path):
    class FakeCloneManager:
        async def clone(self, node):
            path = tmp_path / node.name
            path.mkdir()
            return path

    engine = app.state.engine
    engine.marketplace.clone_manager = FakeCloneManager()
    response = client.post("/marketplace/html-anything/install")
    assert response.status_code == 200
    assert response.json()["installed_globally"] is True


def test_enable_disable_module(client, tmp_path):
    class FakeCloneManager:
        async def clone(self, node):
            path = tmp_path / node.name
            path.mkdir()
            return path

    engine = app.state.engine
    engine.marketplace.clone_manager = FakeCloneManager()
    response = client.post("/marketplace/html-anything/enable?project_id=p1")
    assert response.status_code == 200
    assert "p1" in response.json()["enabled_projects"]
    response = client.post("/marketplace/html-anything/disable?project_id=p1")
    assert response.status_code == 200
    assert "p1" not in response.json()["enabled_projects"]


def test_rate_module(client):
    response = client.post(
        "/marketplace/html-anything/rate",
        json={"user_id": "u1", "score": 5.0, "review": "great"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["average_rating"] == 5.0
    assert data["rating_count"] == 1
