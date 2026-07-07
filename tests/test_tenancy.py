"""Tests for multi-tenancy scaffolding."""

from __future__ import annotations

import asyncio

import pytest

from sahiixx_agency.core.engine import AgencyEngine
from sahiixx_agency.core.models import AgencyConfig


@pytest.fixture
def engine(tmp_path: pytest.TempPathFactory) -> AgencyEngine:
    return AgencyEngine(AgencyConfig(data_dir=str(tmp_path), memory_backend="json"))


def test_create_and_list_tenants(engine: AgencyEngine) -> None:
    t1 = engine.create_tenant("Acme")
    t2 = engine.create_tenant("Globex")
    assert t1.name == "Acme"
    assert t2.name == "Globex"
    tenants = engine.list_tenants()
    assert len(tenants) == 2
    assert {t.name for t in tenants} == {"Acme", "Globex"}


def test_create_and_list_projects(engine: AgencyEngine) -> None:
    tenant = engine.create_tenant("Acme")
    p1 = engine.create_project(tenant.id, "Website")
    p2 = engine.create_project(tenant.id, "Mobile")
    assert p1.tenant_id == tenant.id
    projects = engine.list_projects(tenant_id=tenant.id)
    assert len(projects) == 2
    assert {p.name for p in projects} == {"Website", "Mobile"}


def test_project_secrets(engine: AgencyEngine) -> None:
    tenant = engine.create_tenant("Acme")
    project = engine.create_project(tenant.id, "Website")
    engine.set_project_secret(project.id, "API_KEY", "secret123")
    assert engine.get_project_secret(project.id, "API_KEY") == "secret123"
    assert engine.get_project_secret(project.id, "MISSING") is None


def test_dispatch_with_tenant_and_project(engine: AgencyEngine) -> None:
    tenant = engine.create_tenant("Acme")
    project = engine.create_project(tenant.id, "Website")
    task = asyncio.run(engine.dispatch("list modules", tenant_id=tenant.id, project_id=project.id))
    assert task.tenant_id == tenant.id
    assert task.project_id == project.id
