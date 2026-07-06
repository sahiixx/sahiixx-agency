"""Tests for discovery API endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from sahiixx_agency.api.main import app

client = TestClient(app)


def test_discovery_run_endpoint(monkeypatch):
    async def fake_run(self):
        return []

    mock_engine = MagicMock()
    mock_engine.config.data_dir = "./data"
    mock_engine.config.discovery.min_stars = 50
    mock_engine.config.discovery.auto_clone = False

    monkeypatch.setattr("sahiixx_agency.discovery.pipeline.DiscoveryPipeline.run", fake_run)
    monkeypatch.setattr("sahiixx_agency.api.main._engine", mock_engine)
    response = client.post("/discovery/run")
    assert response.status_code == 200
    assert response.json()["discovered"] == 0
