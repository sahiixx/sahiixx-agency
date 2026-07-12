"""MCP server exposing the agency as tools."""

from __future__ import annotations

import json
import os
from typing import Any

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from sahiixx_agency.core.engine import AgencyEngine
from sahiixx_agency.core.models import AgencyConfig, RepoCategory

mcp = FastMCP("sahiixx-agency")
_engine: AgencyEngine | None = None


def _load_config() -> AgencyConfig:
    config_path = os.environ.get("OPA_CONFIG", "./config/agency.yaml")
    config = AgencyConfig()
    if os.path.exists(config_path):
        import yaml

        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        config = AgencyConfig.model_validate(data)
    return config


def _get_engine() -> AgencyEngine:
    global _engine
    if _engine is None:
        _engine = AgencyEngine(_load_config())
    return _engine


@mcp.custom_route("/health", methods=["GET"])
async def _health_check(_request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


@mcp.tool()
async def list_gcc_outbound_skills() -> str:
    """List available GCC Outbound skills."""
    from sahiixx_agency.adapters.skills.gcc_outbound import GccOutboundSkillAdapter

    adapter = GccOutboundSkillAdapter()
    return json.dumps({"skills": adapter.list_skills()}, indent=2)


@mcp.tool()
async def run_gcc_outbound_skill(skill: str, context: str = "{}") -> str:
    """Run a GCC Outbound skill by name with a JSON context."""

    engine = _get_engine()
    await engine.start_worker()
    data: dict[str, Any] = json.loads(context)
    task = await engine.dispatch(
        f"run gcc {skill} skill",
        {"skill": skill, "context": data},
    )
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
    await engine.start_worker()
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


@mcp.tool()
async def list_workflows() -> str:
    """List agency workflow definitions."""
    engine = _get_engine()
    workflows = engine.workflows.list_definitions()
    return json.dumps([w.model_dump(mode="json") for w in workflows], indent=2)


@mcp.tool()
async def run_workflow(workflow_id: str, context: str = "{}") -> str:
    """Run a workflow instance by id."""
    engine = _get_engine()
    await engine.start_worker()
    data: dict[str, Any] = json.loads(context)
    instance = engine.workflows.create_instance(workflow_id, data)
    if instance is None:
        return json.dumps({"error": "Workflow not found or disabled"})
    result = await engine.workflows.run_instance(instance.id, dispatch=engine.dispatch, notify=engine.notify)
    if result is None:
        return json.dumps({"error": "Workflow instance disappeared"})
    return json.dumps(result.model_dump(mode="json"), indent=2)


@mcp.tool()
async def send_notification(channel: str, title: str, body: str, recipient: str | None = None) -> str:
    """Send an agency notification through a channel (sse, telegram, email, webhook)."""
    engine = _get_engine()
    from sahiixx_agency.core.models import NotificationChannel

    try:
        ch = NotificationChannel(channel)
    except ValueError:
        return f"Unknown channel: {channel}"
    notification = await engine.notify(ch, title, body, recipient)
    return json.dumps(notification.model_dump(mode="json"), indent=2)


@mcp.tool()
async def get_metrics() -> str:
    """Get Prometheus-compatible agency metrics."""
    engine = _get_engine()
    return engine.metrics.to_prometheus()


@mcp.tool()
async def get_health() -> str:
    """Get agency health check results."""
    engine = _get_engine()
    checks = engine.metrics.health()
    return json.dumps(
        {
            "status": engine.metrics.overall_health().value,
            "checks": [c.model_dump(mode="json") for c in checks],
        },
        indent=2,
    )


def main() -> None:
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "sse":
        mcp.settings.host = os.environ.get("MCP_HOST", "0.0.0.0")
        mcp.settings.port = int(os.environ.get("MCP_PORT", "8081"))
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
