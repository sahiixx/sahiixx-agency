from __future__ import annotations

from pathlib import Path

import pytest

from sahiixx_agency.adapters.framework.agentic_framework_adapter import (
    AgenticFrameworkAdapter,
)
from sahiixx_agency.core.models import RepoNode


def _node(framework: str) -> RepoNode:
    return RepoNode(
        id=framework,
        name=framework,
        owner="test",
        full_name=f"test/{framework}",
        url=f"https://github.com/test/{framework}",
    )


@pytest.mark.parametrize("framework", ["rag_anything", "hermes"])
def test_scaffold_generated_and_runnable_syntax(framework, tmp_path):
    """Scaffold for new frameworks should write a syntactically valid Python file."""
    adapter = AgenticFrameworkAdapter(
        framework=framework,
        clone_base_dir=str(tmp_path),
        repo_dir=str(tmp_path / framework),
    )
    result = adapter.dispatch("Answer questions over my PDFs", project_name="demo")
    assert result.status == "simulated"
    scaffold = Path(result.scaffold_path)
    assert scaffold.exists()
    compile(scaffold.read_text(), str(scaffold), "exec")


def test_rag_anything_scaffold_mentions_rag(tmp_path):
    adapter = AgenticFrameworkAdapter(
        framework="rag_anything",
        clone_base_dir=str(tmp_path),
        repo_dir=str(tmp_path / "rag_anything"),
    )
    result = adapter.dispatch("Ingest docs", project_name="p")
    text = Path(result.scaffold_path).read_text()
    assert "RAGAnything" in text
    assert "process_document" in text


def test_hermes_scaffold_mentions_hermes(tmp_path):
    adapter = AgenticFrameworkAdapter(
        framework="hermes",
        clone_base_dir=str(tmp_path),
        repo_dir=str(tmp_path / "hermes"),
    )
    result = adapter.dispatch("Plan my week", project_name="p")
    text = Path(result.scaffold_path).read_text()
    assert "Hermes" in text


@pytest.mark.asyncio
async def test_framework_async_run_simulate(tmp_path):
    adapter = AgenticFrameworkAdapter(
        framework="hermes",
        clone_base_dir=str(tmp_path),
        repo_dir=str(tmp_path / "hermes"),
    )
    result = await adapter.run(_node("hermes"), {"brief": "do a thing", "simulate": True})
    assert result["status"] == "simulated"
    assert result["scaffold_path"].endswith("agent.py")
