"""Tests for the pluggable LLM abstraction and cost tracking."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi.testclient import TestClient

from sahiixx_agency.core.llm import (
    LLMCostTracker,
    LLMManager,
    OpenAICompatibleProvider,
    compute_cost,
    create_provider,
)
from sahiixx_agency.core.memory import AgencyMemory
from sahiixx_agency.core.models import (
    AgencyConfig,
    LLMConfig,
    LLMMessage,
    LLMModelPricing,
    LLMProvider,
    LLMProviderConfig,
    LLMResponse,
    LLMUsage,
)


@pytest.fixture
def memory(tmp_path):
    return AgencyMemory(data_dir=str(tmp_path), backend="json")


@pytest.fixture
def manager(tmp_path, memory):
    config = AgencyConfig(
        data_dir=str(tmp_path),
        llm=LLMConfig(
            default_provider=LLMProvider.OPENAI,
            default_model="gpt-4o-mini",
            providers={
                "openai": LLMProviderConfig(api_key="test-key"),
            },
            pricing={
                "custom-model": LLMModelPricing(input_per_1m_tokens=1.0, output_per_1m_tokens=2.0),
            },
        ),
    )
    return LLMManager(config.llm, memory)


@pytest.mark.asyncio
async def test_openai_provider_chat(monkeypatch):
    provider = OpenAICompatibleProvider("openai", "key", "https://api.openai.com/v1", "gpt-4o-mini")

    async def fake_post(self, url, **kwargs):
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "Hello"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    response = await provider.chat(
        model="gpt-4o-mini",
        messages=[LLMMessage(role="user", content="Hi")],
        temperature=0.7,
        max_tokens=100,
    )
    assert response.content == "Hello"
    assert response.usage.input_tokens == 10
    assert response.usage.output_tokens == 5
    assert response.usage.total_tokens == 15


@pytest.mark.asyncio
async def test_manager_chat_records_cost_and_uses_default_model(manager, monkeypatch):
    async def fake_post(self, url, **kwargs):
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "OK"}}],
                "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    response = await manager.chat(messages=[LLMMessage(role="user", content="Test")])

    assert response.provider == "openai"
    assert response.model == "gpt-4o-mini"
    assert response.content == "OK"
    assert response.usage.total_tokens == 30
    assert response.cost_usd is not None
    assert response.cost_usd > 0

    summary = manager.cost_summary()
    assert summary["total_calls"] == 1
    assert summary["total_tokens"] == 30
    assert summary["total_cost_usd"] == response.cost_usd


def test_compute_cost_uses_default_pricing():
    usage = LLMUsage(input_tokens=1_000_000, output_tokens=500_000)
    cost = compute_cost("gpt-4o-mini", usage, {})
    assert cost is not None
    # 1M * 0.15 + 0.5M * 0.60 = 0.15 + 0.30 = 0.45
    assert cost == pytest.approx(0.45, rel=1e-6)


def test_compute_cost_uses_configured_pricing():
    usage = LLMUsage(input_tokens=1_000_000, output_tokens=1_000_000)
    cost = compute_cost(
        "custom-model",
        usage,
        {"custom-model": LLMModelPricing(input_per_1m_tokens=1.0, output_per_1m_tokens=2.0)},
    )
    assert cost == pytest.approx(3.0, rel=1e-6)


def test_compute_cost_returns_none_for_unknown_model():
    usage = LLMUsage(input_tokens=100, output_tokens=100)
    assert compute_cost("unknown-model", usage, {}) is None


def test_cost_tracker_filters_by_time(memory):
    tracker = LLMCostTracker(memory)
    old_response = LLMResponse(
        provider="openai",
        model="gpt-4o-mini",
        content="x",
        usage=LLMUsage(input_tokens=1, output_tokens=1),
        latency_ms=10,
    )
    old_response.created_at = datetime.now(timezone.utc) - timedelta(days=10)
    tracker.record(old_response)

    new_response = LLMResponse(
        provider="openai",
        model="gpt-4o-mini",
        content="y",
        usage=LLMUsage(input_tokens=2, output_tokens=2),
        latency_ms=10,
    )
    tracker.record(new_response)

    since = datetime.now(timezone.utc) - timedelta(days=1)
    summary = tracker.summary(since=since)
    assert summary["total_calls"] == 1
    assert summary["total_input_tokens"] == 2


def test_create_provider_raises_without_api_key():
    config = LLMConfig(providers={"openai": LLMProviderConfig(api_key=None)})
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        create_provider("openai", config)


def test_list_providers_shows_readiness(manager):
    providers = {p["id"]: p for p in manager.list_providers()}
    assert providers["openai"]["ready"] is True
    assert providers["ollama"]["ready"] is True
    assert providers["anthropic"]["ready"] is False


def test_llm_config_validates_from_dict():
    data = {
        "default_provider": "anthropic",
        "default_model": "claude-3-5-sonnet-20241022",
        "providers": {
            "anthropic": {
                "api_key": "secret",
                "base_url": "https://api.anthropic.com/v1",
            }
        },
    }
    config = LLMConfig.model_validate(data)
    assert config.default_provider == LLMProvider.ANTHROPIC
    assert config.providers["anthropic"].api_key == "secret"


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    from contextlib import asynccontextmanager

    from sahiixx_agency.api.main import app, get_engine
    from sahiixx_agency.core.engine import AgencyEngine
    from sahiixx_agency.core.models import RepoCategory, RepoNode

    config = AgencyConfig(
        data_dir=str(tmp_path),
        llm=LLMConfig(
            default_provider=LLMProvider.OPENAI,
            default_model="gpt-4o-mini",
            providers={"openai": LLMProviderConfig(api_key="test-key")},
        ),
    )
    engine = AgencyEngine(config)
    engine.registry._modules["friday"] = RepoNode(
        id="friday",
        name="friday",
        full_name="sahiixx/friday",
        url="https://github.com/sahiixx/friday",
        category=RepoCategory.VOICE_AI,
        language="python",
        stars=50,
    )

    @asynccontextmanager
    async def _noop_lifespan(_app):
        yield

    app.dependency_overrides[get_engine] = lambda: engine
    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = _noop_lifespan
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.router.lifespan_context = original_lifespan


def test_api_llm_providers(api_client):
    resp = api_client.get("/llm/providers")
    assert resp.status_code == 200
    data = resp.json()
    assert any(p["id"] == "openai" for p in data)


def test_api_llm_chat(api_client, monkeypatch):
    async def fake_post(self, url, **kwargs):
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "API says hi"}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    resp = api_client.post(
        "/llm/chat",
        json={"messages": [{"role": "user", "content": "Hi"}]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == "API says hi"
    assert data["usage"]["total_tokens"] == 8


def test_api_llm_costs(api_client, monkeypatch):
    async def fake_post(self, url, **kwargs):
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "x"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    api_client.post("/llm/chat", json={"messages": [{"role": "user", "content": "Hi"}]})

    resp = api_client.get("/llm/costs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_calls"] == 1
    assert data["total_tokens"] == 15


def test_api_llm_chat_missing_messages(api_client):
    resp = api_client.post("/llm/chat", json={"messages": []})
    assert resp.status_code == 422


def test_api_llm_chat_records_tenant_and_project_cost_attribution(api_client, monkeypatch):
    async def fake_post(self, url, **kwargs):
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "Attributed"}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    resp = api_client.post(
        "/llm/chat",
        json={
            "messages": [{"role": "user", "content": "Hi"}],
            "tenant_id": "tenant_acme",
            "project_id": "project_roadmap",
        },
    )
    assert resp.status_code == 200

    costs_resp = api_client.get("/costs?tenant_id=tenant_acme&project_id=project_roadmap")
    assert costs_resp.status_code == 200
    records = costs_resp.json()
    assert len(records) == 1
    assert records[0]["tenant_id"] == "tenant_acme"
    assert records[0]["project_id"] == "project_roadmap"
    assert records[0]["category"] == "llm"
