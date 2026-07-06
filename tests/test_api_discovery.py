"""Tests for discovery API endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from sahiixx_agency.api.main import app

client = TestClient(app)


def test_discovery_run_endpoint(monkeypatch):
    async def fake_run(self):
        return []

    monkeypatch.setattr("sahiixx_agency.discovery.pipeline.DiscoveryPipeline.run", fake_run)
    response = client.post("/discovery/run")
    assert response.status_code == 200
    assert response.json()["discovered"] == 0
