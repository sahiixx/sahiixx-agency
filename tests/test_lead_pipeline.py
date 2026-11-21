"""Offline HTTP contract checks: capture -> qualify -> curated area matching."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sahiixx_agency.adapters.base import BaseAdapter
from sahiixx_agency.api.lead_machine import router


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Isolate adapter scratch directories and avoid the production app lifespan,
    # which can sync GitHub and start workers. No customer data or network needed.
    original_init = BaseAdapter.__init__

    def isolated_init(self, *args, **kwargs):
        kwargs["clone_base_dir"] = str(tmp_path / "repos")
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(BaseAdapter, "__init__", isolated_init)
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as http:
        yield http


@pytest.mark.parametrize("prefix", ["/opa", "/api/opa"])
def test_qualified_pipeline_preserves_identity_and_area(client, prefix):
    response = client.post(
        f"{prefix}/lead/pipeline",
        json={
            "message": "I want to buy in Palm Jumeirah, budget AED 5mn, in 2 months",
            "source": "nexus_whatsapp",
            "raw_ref": "fixture_message",
            "captured_at": "2026-11-05T00:00:00+00:00",
        },
    )
    assert response.status_code == 200
    data = response.json()
    lead_id = data["captured"]["lead_id"]
    assert lead_id.startswith("lead_")
    assert data["qualified"]["lead_id"] == data["matched"]["lead_id"] == lead_id
    assert data["captured"]["raw_ref"] == "fixture_message"
    assert data["captured"]["captured_at"] == "2026-11-05T00:00:00+00:00"
    assert data["qualified"]["budget_band"] == "3M_10M"
    assert data["matched"]["matches"][0]["area"] == "Palm Jumeirah"


@pytest.mark.parametrize("message", ["Tell me about Dubai", "I want to buy someday"])
def test_unqualified_leads_do_not_invoke_matching(client, message):
    with patch("sahiixx_agency.adapters.geomatch_agent.GeoMatchAgent.execute", new_callable=AsyncMock) as match:
        response = client.post("/opa/lead/pipeline", json={"message": message})
    assert response.status_code == 200
    assert response.json()["qualified"]["status"] != "qualified"
    assert response.json()["matched"] is None
    match.assert_not_awaited()


@pytest.mark.parametrize("endpoint", ["capture", "qualify", "pipeline"])
def test_blank_message_rejected(client, endpoint):
    assert client.post(f"/opa/lead/{endpoint}", json={"message": "  "}).status_code == 422


def test_direct_qualification_generates_lead_id(client):
    response = client.post("/opa/lead/qualify", json={"message": "Buy in Marina, budget 1.2M, ASAP"})
    assert response.status_code == 200
    assert response.json()["lead_id"].startswith("lead_")


def test_lead_adapters_registered_without_asgi_import(tmp_path):
    from sahiixx_agency.core.engine import _SPECIALIZED_ADAPTERS
    from sahiixx_agency.core.models import AgencyConfig, AgencyTask

    config = AgencyConfig(data_dir=str(tmp_path))
    for name, expected in [("lead_capture", "LeadCaptureAgent"), ("geomatch", "GeoMatchAgent")]:
        adapter, payload = _SPECIALIZED_ADAPTERS[name](
            config,
            None,
            None,
            AgencyTask(id="task_fixture", intent="fixture", payload={"lead_id": "fixture"}),
        )
        assert type(adapter).__name__ == expected
        assert payload["lead_id"] == "fixture"


def test_cli_serve_uses_complete_api_entrypoint(monkeypatch):
    import uvicorn

    from sahiixx_agency.cli.main import serve

    # Only inspect launch arguments; never start a server.
    run = Mock()
    monkeypatch.setattr(uvicorn, "run", run)
    serve(host="127.0.0.1", port=8082, reload=False)
    run.assert_called_once_with("sahiixx_agency.api.asgi:app", host="127.0.0.1", port=8082, reload=False)


def test_asgi_pipeline_obeys_api_key_gate(monkeypatch, tmp_path):
    from sahiixx_agency.api.asgi import app

    monkeypatch.setenv("OPA_API_KEY", "synthetic-test-key")
    original_init = BaseAdapter.__init__

    def isolated_init(self, *args, **kwargs):
        kwargs["clone_base_dir"] = str(tmp_path / "repos")
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(BaseAdapter, "__init__", isolated_init)
    # No context manager: skip the live app lifespan and background sync.
    http = TestClient(app)
    try:
        payload = {"message": "I want to buy in Marina, budget 1.2M, ASAP"}
        assert http.post("/api/opa/lead/pipeline", json=payload).status_code == 401
        response = http.post(
            "/api/opa/lead/pipeline",
            json=payload,
            headers={"X-OPA-API-Key": "synthetic-test-key"},
        )
        assert response.status_code == 200
        assert response.json()["matched"]["status"] == "matched"
    finally:
        http.close()
