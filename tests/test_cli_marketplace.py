from __future__ import annotations

import pytest
from typer.testing import CliRunner

from sahiixx_agency.cli.main import app
from sahiixx_agency.core.engine import AgencyEngine
from sahiixx_agency.core.models import AgencyConfig, RepoCategory, RepoNode


@pytest.fixture
def patched_engine(tmp_path, monkeypatch):
    config = {"data_dir": str(tmp_path), "memory_backend": "json"}
    engine = AgencyEngine(AgencyConfig.model_validate(config))
    node = RepoNode(
        id="html-anything",
        name="html-anything",
        full_name="nexu-io/html-anything",
        url="https://github.com/nexu-io/html-anything",
        category=RepoCategory.COOKBOOK,
    )
    engine.registry._modules[node.id] = node
    engine.registry.save()
    monkeypatch.setattr("sahiixx_agency.cli.main.get_engine", lambda: engine)
    return engine


runner = CliRunner()


def test_marketplace_list(patched_engine):
    result = runner.invoke(app, ["marketplace"])
    assert result.exit_code == 0
    assert "html-anything" in result.stdout


def test_marketplace_install(patched_engine, tmp_path):
    class FakeCloneManager:
        async def clone(self, node):
            path = tmp_path / node.name
            path.mkdir()
            return path

    patched_engine.marketplace.clone_manager = FakeCloneManager()
    result = runner.invoke(app, ["marketplace", "install", "html-anything"])
    assert result.exit_code == 0
    assert "installed" in result.stdout.lower()


def test_marketplace_enable_disable(patched_engine, tmp_path):
    class FakeCloneManager:
        async def clone(self, node):
            path = tmp_path / node.name
            path.mkdir()
            return path

    patched_engine.marketplace.clone_manager = FakeCloneManager()
    result = runner.invoke(app, ["marketplace", "enable", "html-anything", "--project", "p1"])
    assert result.exit_code == 0
    result = runner.invoke(app, ["marketplace", "disable", "html-anything", "--project", "p1"])
    assert result.exit_code == 0


def test_marketplace_rate(patched_engine):
    result = runner.invoke(app, ["marketplace", "rate", "html-anything", "5"])
    assert result.exit_code == 0
    assert "rated" in result.stdout.lower()
