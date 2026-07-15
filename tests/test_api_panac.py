"""Panac command-center API tests."""

from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient

from sahiixx_agency.api.main import app
from sahiixx_agency.core.memory import AgencyMemory


@pytest.fixture
def client(tmp_path):
    """Use the Panac router without starting unrelated agency workers."""
    @asynccontextmanager
    async def noop_lifespan(_app):
        yield

    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = noop_lifespan
    app.state.panac_memory = AgencyMemory(str(tmp_path))
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.router.lifespan_context = original_lifespan
        del app.state.panac_memory


def test_panac_overview_has_unified_operating_data(client):
    response = client.get("/panac/overview")

    assert response.status_code == 200
    data = response.json()
    assert data["demo_mode"] is True
    assert len(data["metrics"]) == 4
    assert {signal["domain"] for signal in data["signals"]} >= {"revenue", "inventory", "compliance"}


def test_panac_approval_records_a_decision_only(client):
    response = client.post("/panac/recommendations/rec_price_001/approve")

    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_panac_import_requires_source_columns(client):
    response = client.post("/panac/imports", json={"source": "contracts", "records": [{"contract_id": "C-1"}]})

    assert response.status_code == 422
    assert "customer" in response.json()["detail"]


def test_panac_import_persists_a_validated_summary(client):
    response = client.post(
        "/panac/imports",
        json={
            "source": "contracts",
            "records": [{"contract_id": "C-1", "customer": "Northstar", "start_date": "2026-01-01", "end_date": "2026-12-31", "value": 12000}],
        },
    )

    assert response.status_code == 201
    assert response.json()["records_imported"] == 1
    assert client.get("/panac/imports").json()[0]["source"] == "contracts"
    overview = client.get("/panac/overview").json()
    assert overview["demo_mode"] is False
    assert overview["metrics"][0]["value"] == "$12,000"


def test_panac_generates_review_only_revenue_schedule(client):
    client.post(
        "/panac/imports",
        json={"source": "contracts", "records": [{"contract_id": "C-2", "customer": "Northstar", "start_date": "2026-01-01", "end_date": "2026-12-31", "value": 12000}]},
    )

    response = client.get("/panac/revenue-recognition", params={"as_of": "2026-07-01"})

    assert response.status_code == 200
    assert response.json()["recognized_value"] == 5983.56
    assert response.json()["deferred_value"] == 6016.44
    assert "not an ASC 606 determination" in response.json()["disclaimer"]


def test_panac_flags_inventory_coverage_from_usage(client):
    client.post("/panac/imports", json={"source": "usage", "records": [{"account_id": "A-1", "date": "2026-06-01", "metric": "SKU-1", "quantity": 10}, {"account_id": "A-1", "date": "2026-06-02", "metric": "SKU-1", "quantity": 10}]})
    client.post("/panac/imports", json={"source": "inventory", "records": [{"sku": "SKU-1", "location": "Dubai", "available_quantity": 100}]})

    response = client.get("/panac/demand-planning")

    assert response.status_code == 200
    forecast = response.json()["forecasts"][0]
    assert forecast["projected_30_day_demand"] == 300
    assert forecast["coverage_days"] == 10
    assert forecast["risk"] == "critical"
