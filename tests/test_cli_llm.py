"""Tests for the LLM CLI commands."""

from __future__ import annotations

import httpx
import pytest
from typer.testing import CliRunner

from sahiixx_agency.cli.main import app

runner = CliRunner()


@pytest.fixture
def patched_llm_engine(monkeypatch, tmp_path):
    from sahiixx_agency.core.engine import AgencyEngine
    from sahiixx_agency.core.models import AgencyConfig, LLMConfig, LLMProviderConfig

    config = AgencyConfig(
        data_dir=str(tmp_path),
        llm=LLMConfig(
            default_provider="openai",
            default_model="gpt-4o-mini",
            providers={"openai": LLMProviderConfig(api_key="test-key")},
        ),
    )
    engine = AgencyEngine(config)
    monkeypatch.setattr("sahiixx_agency.cli.main.AgencyEngine", lambda config=None: engine)
    return engine


def test_llm_providers_command(patched_llm_engine):
    result = runner.invoke(app, ["llm", "providers"])
    assert result.exit_code == 0
    assert "openai" in result.stdout.lower()


def test_llm_chat_command(patched_llm_engine, monkeypatch):
    async def fake_post(self, url, **kwargs):
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "CLI response"}}],
                "usage": {"prompt_tokens": 4, "completion_tokens": 4, "total_tokens": 8},
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    result = runner.invoke(app, ["llm", "chat", "hello"])
    assert result.exit_code == 0
    assert "CLI response" in result.stdout


def test_llm_costs_command(patched_llm_engine, monkeypatch):
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
    runner.invoke(app, ["llm", "chat", "count this"])

    result = runner.invoke(app, ["llm", "costs", "--days", "1"])
    assert result.exit_code == 0
    assert "calls" in result.stdout.lower()


def test_llm_chat_command_records_tenant_project_cost_attribution(patched_llm_engine, monkeypatch):
    async def fake_post(self, url, **kwargs):
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "Attributed CLI response"}}],
                "usage": {"prompt_tokens": 4, "completion_tokens": 4, "total_tokens": 8},
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    result = runner.invoke(
        app,
        ["llm", "chat", "hello", "--tenant", "tenant_cli", "--project", "project_cli"],
    )
    assert result.exit_code == 0
    assert "Attributed CLI response" in result.stdout

    # Verify the cost ledger captured the attribution.
    records = patched_llm_engine.cost_ledger.list_records(
        tenant_id="tenant_cli",
        project_id="project_cli",
        category="llm",
    )
    assert len(records) == 1
    assert records[0].tenant_id == "tenant_cli"
    assert records[0].project_id == "project_cli"
    assert records[0].category == "llm"
