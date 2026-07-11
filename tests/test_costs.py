"""Tests for per-tenant/per-project cost tracking."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from typer.testing import CliRunner

from sahiixx_agency.api.main import get_engine
from sahiixx_agency.cli.main import app as cli_app
from sahiixx_agency.core.costs import CostLedger
from sahiixx_agency.core.engine import AgencyEngine
from sahiixx_agency.core.llm import LLMManager
from sahiixx_agency.core.memory import AgencyMemory
from sahiixx_agency.core.models import (
    AgencyConfig,
    AgencyTask,
    CostRecord,
    LLMConfig,
    LLMMessage,
    LLMProvider,
    LLMProviderConfig,
    RepoCategory,
    RepoNode,
    TaskStatus,
)

runner = CliRunner()


@pytest.fixture
def memory(tmp_path):
    return AgencyMemory(data_dir=str(tmp_path), backend="json")


@pytest.fixture
def ledger(memory):
    return CostLedger(memory)


@pytest.fixture
def patched_engine(monkeypatch, tmp_path):
    config = AgencyConfig(data_dir=str(tmp_path))
    engine = AgencyEngine(config)

    fake_modules = [
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
    for module in fake_modules:
        engine.registry._modules[module.id] = module

    async def fake_discover(username: str) -> list[RepoNode]:
        for module in fake_modules:
            engine.registry._modules[module.id] = module
        return fake_modules

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

    monkeypatch.setattr("sahiixx_agency.cli.main.AgencyEngine", lambda config=None: engine)
    return engine


def test_cost_record_defaults():
    record = CostRecord(category="llm", amount=1.23)
    assert record.category == "llm"
    assert record.amount == 1.23
    assert record.currency == "USD"
    assert record.tenant_id is None
    assert record.project_id is None
    assert record.task_id is None
    assert record.id.startswith("cost_")
    assert isinstance(record.timestamp, datetime)


def test_cost_record_validates_negative_amount():
    with pytest.raises(ValidationError):
        CostRecord(category="llm", amount=-1.0)


def test_ledger_record_persists_cost(memory, ledger):
    record = CostRecord(
        tenant_id="tenant_a",
        project_id="project_1",
        task_id="task_abc",
        category="llm",
        amount=0.42,
        description="test llm call",
    )
    ledger.record(record)

    events = memory.recent_events(topic="cost.record", limit=10)
    assert len(events) == 1
    assert events[0]["payload"]["category"] == "llm"
    assert events[0]["payload"]["amount"] == 0.42


def test_ledger_list_records_filters_by_tenant_and_project(memory, ledger):
    ledger.record(CostRecord(tenant_id="t1", project_id="p1", category="llm", amount=1.0))
    ledger.record(CostRecord(tenant_id="t1", project_id="p2", category="llm", amount=2.0))
    ledger.record(CostRecord(tenant_id="t2", project_id="p1", category="execution", amount=3.0))

    all_records = ledger.list_records()
    assert len(all_records) == 3

    t1 = ledger.list_records(tenant_id="t1")
    assert len(t1) == 2
    assert sum(r.amount for r in t1) == 3.0

    p1 = ledger.list_records(project_id="p1")
    assert len(p1) == 2

    t1_p1 = ledger.list_records(tenant_id="t1", project_id="p1")
    assert len(t1_p1) == 1
    assert t1_p1[0].amount == 1.0


def test_ledger_summary_aggregates_by_category(memory, ledger):
    ledger.record(CostRecord(tenant_id="t1", project_id="p1", category="llm", amount=1.5))
    ledger.record(CostRecord(tenant_id="t1", project_id="p1", category="llm", amount=2.5))
    ledger.record(CostRecord(tenant_id="t1", project_id="p1", category="execution", amount=0.5))

    summary = ledger.summary(tenant_id="t1", project_id="p1")
    assert summary["total"] == 4.5
    assert summary["by_category"]["llm"] == 4.0
    assert summary["by_category"]["execution"] == 0.5
    assert summary["currency"] == "USD"
    assert summary["record_count"] == 3


def test_ledger_summary_filters_by_tenant(memory, ledger):
    ledger.record(CostRecord(tenant_id="t1", category="llm", amount=10.0))
    ledger.record(CostRecord(tenant_id="t2", category="llm", amount=5.0))

    assert ledger.summary(tenant_id="t1")["total"] == 10.0
    assert ledger.summary(tenant_id="t2")["total"] == 5.0
    assert ledger.summary()["total"] == 15.0


@pytest.mark.asyncio
async def test_llm_tracker_records_cost_with_task_tenant_project(memory, monkeypatch):
    from sahiixx_agency.core.costs import CostLedger

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

    ledger = CostLedger(memory)
    config = LLMConfig(
        default_provider=LLMProvider.OPENAI,
        providers={"openai": LLMProviderConfig(api_key="test-key")},
    )
    manager = LLMManager(config, memory, ledger=ledger)

    task = AgencyTask(
        id="task_xyz",
        intent="say hello",
        tenant_id="tenant_1",
        project_id="project_1",
        status=TaskStatus.RUNNING,
    )

    await manager.chat(
        messages=[LLMMessage(role="user", content="Hi")],
        provider="openai",
        model="gpt-4o-mini",
        task=task,
    )

    records = ledger.list_records()
    assert len(records) == 1
    assert records[0].category == "llm"
    assert records[0].tenant_id == "tenant_1"
    assert records[0].project_id == "project_1"
    assert records[0].task_id == "task_xyz"
    # gpt-4o-mini pricing: 10 in * 0.15/1M + 5 out * 0.60/1M = 0.0000045 -> rounded 0.000005
    assert records[0].amount == pytest.approx(0.000005, rel=1e-6)


def test_ledger_list_records_filters_by_category(memory, ledger):
    ledger.record(CostRecord(category="llm", amount=1.0))
    ledger.record(CostRecord(category="execution", amount=2.0))
    ledger.record(CostRecord(category="llm", amount=3.0))

    llm_records = ledger.list_records(category="llm")
    assert len(llm_records) == 2
    assert sum(r.amount for r in llm_records) == 4.0


def test_ledger_list_records_respects_limit(memory, ledger):
    for i in range(5):
        ledger.record(CostRecord(category="llm", amount=float(i)))

    assert len(ledger.list_records(limit=2)) == 2
    assert len(ledger.list_records(limit=10)) == 5


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    from contextlib import asynccontextmanager

    from sahiixx_agency.api.main import app, get_engine
    from sahiixx_agency.core.engine import AgencyEngine

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


def test_api_costs_endpoint_returns_records(api_client):
    engine = api_client.app.dependency_overrides[get_engine]()
    engine.cost_ledger.record(
        CostRecord(tenant_id="tenant_a", project_id="project_1", category="llm", amount=1.23)
    )

    resp = api_client.get("/costs")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["tenant_id"] == "tenant_a"
    assert data[0]["project_id"] == "project_1"
    assert data[0]["category"] == "llm"
    assert data[0]["amount"] == 1.23


def test_api_costs_endpoint_filters_by_tenant_and_project(api_client):
    engine = api_client.app.dependency_overrides[get_engine]()
    engine.cost_ledger.record(CostRecord(tenant_id="t1", project_id="p1", category="llm", amount=1.0))
    engine.cost_ledger.record(CostRecord(tenant_id="t1", project_id="p2", category="llm", amount=2.0))
    engine.cost_ledger.record(CostRecord(tenant_id="t2", project_id="p1", category="llm", amount=3.0))

    resp = api_client.get("/costs?tenant_id=t1&project_id=p1")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["amount"] == 1.0


def test_api_costs_summary_endpoint(api_client):
    engine = api_client.app.dependency_overrides[get_engine]()
    engine.cost_ledger.record(CostRecord(tenant_id="t1", project_id="p1", category="llm", amount=2.0))
    engine.cost_ledger.record(CostRecord(tenant_id="t1", project_id="p1", category="execution", amount=0.5))

    resp = api_client.get("/costs/summary?tenant_id=t1&project_id=p1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2.5
    assert data["by_category"]["llm"] == 2.0
    assert data["by_category"]["execution"] == 0.5
    assert data["record_count"] == 2


def test_api_costs_records_llm_call_with_task_context(api_client, monkeypatch):
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

    engine = api_client.app.dependency_overrides[get_engine]()
    task = AgencyTask(
        id="task_xyz",
        intent="run voice assistant",
        tenant_id="t1",
        project_id="p1",
        status=TaskStatus.RUNNING,
    )

    import asyncio

    asyncio.run(engine.llm_manager.chat(messages=[LLMMessage(role="user", content="Hi")], task=task))

    records = engine.cost_ledger.list_records()
    assert len(records) == 1
    assert records[0].category == "llm"
    assert records[0].tenant_id == "t1"
    assert records[0].project_id == "p1"
    assert records[0].task_id == "task_xyz"


def test_cli_costs_summary(patched_engine, monkeypatch):
    patched_engine.cost_ledger.record(
        CostRecord(tenant_id="tenant_x", project_id="project_y", category="llm", amount=5.0)
    )

    result = runner.invoke(cli_app, ["costs", "--tenant", "tenant_x", "--summary"])
    assert result.exit_code == 0
    assert "Cost Summary" in result.stdout
    assert "$5.000000" in result.stdout


def test_cli_costs_list_records(patched_engine, monkeypatch):
    patched_engine.cost_ledger.record(
        CostRecord(tenant_id="tenant_x", project_id="project_y", category="llm", amount=5.0)
    )

    result = runner.invoke(cli_app, ["costs", "--tenant", "tenant_x"])
    assert result.exit_code == 0
    assert "Cost Records" in result.stdout
    assert "llm" in result.stdout


def test_cli_costs_empty(patched_engine, monkeypatch):
    monkeypatch.setattr("sahiixx_agency.cli.main.AgencyEngine", lambda config=None: patched_engine)

    result = runner.invoke(cli_app, ["costs"])
    assert result.exit_code == 0
    assert "No cost records found" in result.stdout


def test_ledger_list_records_limit_after_filter(memory, ledger):
    """``limit`` must be applied after filtering, not to the raw event window."""
    # Matching records first, then non-matching records that become most recent.
    for i in range(3):
        ledger.record(CostRecord(category="llm", amount=float(i + 1)))
    for i in range(5):
        ledger.record(CostRecord(category="execution", amount=float(i + 1)))

    # Old behaviour applied limit to unfiltered events: the 5 execution records are
    # most recent, so a small limit would miss the llm records entirely.
    llm_records = ledger.list_records(category="llm", limit=2)
    assert len(llm_records) == 2
    assert all(r.category == "llm" for r in llm_records)
    # All matching records are available, only limited to 2.
    assert len(ledger.list_records(category="llm")) == 3


@pytest.mark.asyncio
async def test_engine_llm_chat_attribution(tmp_path, monkeypatch):
    """``engine.llm_chat(task=...)`` propagates task context to the cost record."""

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

    config = AgencyConfig(
        data_dir=str(tmp_path),
        llm=LLMConfig(
            default_provider=LLMProvider.OPENAI,
            providers={"openai": LLMProviderConfig(api_key="test-key")},
        ),
    )
    engine = AgencyEngine(config)
    task = AgencyTask(
        id="task_attributed",
        intent="say hello",
        tenant_id="tenant_1",
        project_id="project_1",
        status=TaskStatus.RUNNING,
    )

    await engine.llm_chat(
        messages=[LLMMessage(role="user", content="Hi")],
        provider="openai",
        model="gpt-4o-mini",
        task=task,
    )

    records = engine.cost_ledger.list_records(category="llm")
    assert len(records) == 1
    assert records[0].tenant_id == "tenant_1"
    assert records[0].project_id == "project_1"
    assert records[0].task_id == "task_attributed"


@pytest.mark.asyncio
async def test_execute_task_no_zero_amount_execution_cost(tmp_path, monkeypatch):
    """Adapter runs with a zero execution price must not create execution cost records."""
    from sahiixx_agency.adapters.generic_adapter import GenericAdapter

    async def fake_generic_run(self, node: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "success", "module": node.name}

    monkeypatch.setattr(GenericAdapter, "run", fake_generic_run)

    config = AgencyConfig(data_dir=str(tmp_path))
    engine = AgencyEngine(config)
    engine.registry._modules["demo"] = RepoNode(
        id="demo",
        name="demo",
        owner="test",
        full_name="test/demo",
        url="https://github.com/test/demo",
        category=RepoCategory.UNCATEGORIZED,
    )

    task = AgencyTask(
        id="task_demo",
        intent="run the demo repo",
        module_id="demo",
        status=TaskStatus.RUNNING,
    )
    await engine._execute_task(task)

    assert task.status == TaskStatus.COMPLETED
    execution_records = engine.cost_ledger.list_records(category="execution")
    assert len(execution_records) == 0
