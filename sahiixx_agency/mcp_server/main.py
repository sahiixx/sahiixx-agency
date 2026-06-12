"""MCP server exposing the agency as tools."""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from sahiixx_agency.core.engine import AgencyEngine
from sahiixx_agency.core.models import AgencyConfig, RepoCategory

mcp = FastMCP("sahiixx-agency")
_engine: AgencyEngine | None = None


def _get_engine() -> AgencyEngine:
    global _engine
    if _engine is None:
        _engine = AgencyEngine(AgencyConfig())
    return _engine


@mcp.tool()
async def list_modules(category: str | None = None) -> str:
    """List agency modules, optionally filtered by category."""
    engine = _get_engine()
    modules = engine.registry.modules
    if category:
        try:
            cat = RepoCategory(category)
            modules = [m for m in modules if m.category == cat]
        except ValueError:
            return f"Unknown category: {category}. Valid: {[c.value for c in RepoCategory]}"
    modules.sort(key=lambda m: m.stars, reverse=True)
    result = []
    for m in modules[:30]:
        result.append(
            {
                "name": m.name,
                "category": m.category.value,
                "language": m.language,
                "stars": m.stars,
                "url": m.url,
                "capabilities": m.capabilities,
            }
        )
    return json.dumps(result, indent=2)


@mcp.tool()
async def dispatch_task(intent: str, payload: str = "{}") -> str:
    """Dispatch a task through the agency."""
    engine = _get_engine()
    data: dict[str, Any] = json.loads(payload)
    task = await engine.dispatch(intent, data)
    return json.dumps(
        {
            "task_id": task.id,
            "status": task.status.value,
            "module": task.module_id,
            "category": task.category.value if task.category else None,
            "result": task.result,
            "error": task.error,
        },
        indent=2,
    )


@mcp.tool()
async def run_intel_scout(report_type: str = "trending") -> str:
    """Run the GitHub intelligence scout."""
    engine = _get_engine()
    report = await engine.run_intel_scout(report_type)
    return json.dumps(
        {
            "report_id": report.id,
            "type": report.report_type,
            "repos_found": len(report.repos),
            "summary": report.summary,
            "top_repos": [
                {"name": r.name, "stars": r.stars, "language": r.language, "url": r.url} for r in report.repos[:10]
            ],
        },
        indent=2,
    )


@mcp.tool()
async def agency_stats() -> str:
    """Get agency statistics."""
    return json.dumps(_get_engine().stats(), indent=2)


@mcp.tool()
async def sync_registry(username: str = "sahiixx") -> str:
    """Sync GitHub repos into the agency registry."""
    engine = _get_engine()
    discovered = await engine.sync_repos(username)
    return json.dumps({"synced": len(discovered), "username": username}, indent=2)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
