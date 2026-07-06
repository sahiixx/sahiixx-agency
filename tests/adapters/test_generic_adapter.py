from __future__ import annotations

import pytest

from sahiixx_agency.adapters.generic_adapter import GenericAdapter
from sahiixx_agency.core.models import RepoCategory, RepoNode


@pytest.mark.asyncio
async def test_generic_adapter_runs_inferred_command(tmp_path, monkeypatch):
    repo = tmp_path / "demo"
    repo.mkdir()
    (repo / "main.py").write_text("print('hello from demo')")

    node = RepoNode(
        id="demo",
        name="demo",
        owner="test",
        full_name="test/demo",
        url="https://github.com/test/demo",
        category=RepoCategory.UNCATEGORIZED,
    )

    adapter = GenericAdapter(data_dir=str(tmp_path))
    result = await adapter.run(node, {"command": "python main.py"})
    assert result["status"] == "success"
    assert "hello from demo" in result["stdout"]


@pytest.mark.asyncio
async def test_generic_adapter_simulates_when_no_local_clone():
    node = RepoNode(
        id="missing",
        name="missing",
        owner="test",
        full_name="test/missing",
        url="https://github.com/test/missing",
    )
    adapter = GenericAdapter(data_dir="/nonexistent")
    result = await adapter.run(node, {})
    assert result["status"] == "simulated"
