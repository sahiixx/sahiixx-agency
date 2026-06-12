"""FastAPI server for the One Person Agency."""

from __future__ import annotations

import os
import re
import tomllib
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from sahiixx_agency.core.engine import AgencyEngine
from sahiixx_agency.core.models import AgencyConfig, RepoCategory

_engine: AgencyEngine | None = None


def get_engine() -> AgencyEngine:
    if _engine is None:
        raise RuntimeError("Engine not initialized")
    return _engine


class TaskCreateRequest(BaseModel):
    """Request body for creating a new agency task."""

    intent: str
    payload: dict[str, Any] | None = None
    module_id: str | None = None
    category: str | None = None


class SchedulerStartRequest(BaseModel):
    """Request body for starting the registry auto-sync scheduler."""

    interval_minutes: int | None = None


PYPROJECT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "pyproject.toml")


def _get_project_info() -> dict[str, str]:
    """Read package name and version from pyproject.toml."""
    default_name = "One Person Agency"
    default_version = "1.0.0"
    try:
        if tomllib is not None:
            with open(PYPROJECT_PATH, mode="rb") as f:
                data = tomllib.load(f)
            project = data.get("project", {})
            return {
                "name": project.get("name", default_name),
                "version": project.get("version", default_version),
            }
        with open(PYPROJECT_PATH, encoding="utf-8") as f:
            content = f.read()
        name_match = re.search(r'^\s*name\s*=\s*"([^"]+)"', content, re.MULTILINE)
        version_match = re.search(r'^\s*version\s*=\s*"([^"]+)"', content, re.MULTILINE)
        return {
            "name": name_match.group(1) if name_match else default_name,
            "version": version_match.group(1) if version_match else default_version,
        }
    except Exception:
        return {"name": default_name, "version": default_version}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _engine
    config_path = os.environ.get("OPA_CONFIG", "./config/agency.yaml")
    config = AgencyConfig()
    if os.path.exists(config_path):
        import yaml

        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        config = AgencyConfig.model_validate(data)
    _engine = AgencyEngine(config)
    # Auto-sync on startup if registry is empty
    if not _engine.registry.modules:
        await _engine.sync_repos(config.github_username)
    await _engine.start_worker()
    await _engine.start_scheduler()
    yield
    await _engine.stop_scheduler()
    await _engine.stop_worker()
    _engine = None


app = FastAPI(
    title="One Person Agency",
    description="Unified AI orchestration for all repos",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Health & Status ----------


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": "One Person Agency", "version": "1.0.0", "status": "running"}


@app.get("/health")
async def health() -> dict[str, Any]:
    engine = get_engine()
    return {"status": "healthy", "registry_count": len(engine.registry.modules)}


@app.get("/status")
async def get_status() -> dict[str, str]:
    info = _get_project_info()
    return {"name": info["name"], "version": info["version"], "status": "running"}


@app.get("/stats")
async def stats() -> dict[str, Any]:
    return get_engine().stats()


# ---------- Registry ----------


@app.get("/registry")
async def list_registry(
    category: str | None = Query(None),
    language: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[dict[str, Any]]:
    engine = get_engine()
    modules = engine.registry.modules
    if category:
        try:
            cat = RepoCategory(category)
            modules = [m for m in modules if m.category == cat]
        except ValueError as err:
            raise HTTPException(status_code=400, detail=f"Unknown category: {category}") from err
    if language:
        modules = [m for m in modules if m.language and m.language.lower() == language.lower()]
    modules.sort(key=lambda m: m.stars, reverse=True)
    return [m.model_dump(mode="json") for m in modules[offset : offset + limit]]


@app.get("/registry/{module_id}")
async def get_module(module_id: str) -> dict[str, Any]:
    mod = get_engine().registry.get(module_id)
    if not mod:
        raise HTTPException(status_code=404, detail="Module not found")
    return mod.model_dump(mode="json")


@app.post("/registry/sync")
async def sync_registry(username: str | None = Query(None)) -> dict[str, Any]:
    engine = get_engine()
    discovered = await engine.sync_repos(username or engine.config.github_username)
    return {
        "synced": len(discovered),
        "username": username or engine.config.github_username,
    }


# ---------- Tasks ----------


@app.post("/tasks", status_code=status.HTTP_202_ACCEPTED)
async def create_task(request: TaskCreateRequest) -> dict[str, Any]:
    engine = get_engine()
    category: RepoCategory | None = None
    if request.category:
        try:
            category = RepoCategory(request.category)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid category: {request.category}",
            ) from err
    task = await engine.submit_task(
        request.intent,
        payload=request.payload,
        module_id=request.module_id,
        category=category,
    )
    return task.model_dump(mode="json")


@app.get("/tasks")
async def list_tasks(limit: int = Query(50, ge=1, le=200)) -> list[dict[str, Any]]:
    tasks = get_engine().list_tasks(limit=limit)
    return [task.model_dump(mode="json") for task in tasks]


@app.get("/tasks/{task_id}")
async def get_task(task_id: str) -> dict[str, Any]:
    task = get_engine().get_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task.model_dump(mode="json")


@app.get("/worker/status")
async def worker_status() -> dict[str, Any]:
    engine = get_engine()
    return {
        "running": engine.worker_running,
        "queue_size": engine.queue_size,
    }


@app.get("/scheduler/status")
async def scheduler_status() -> dict[str, Any]:
    return get_engine().scheduler_status()


@app.post("/scheduler/start")
async def scheduler_start(request: SchedulerStartRequest) -> dict[str, Any]:
    engine = get_engine()
    await engine.start_scheduler(request.interval_minutes)
    return engine.scheduler_status()


@app.post("/scheduler/stop")
async def scheduler_stop() -> dict[str, Any]:
    engine = get_engine()
    await engine.stop_scheduler()
    return engine.scheduler_status()


@app.post("/tasks/{module_id:path}/execute")
async def execute_module(
    module_id: str,
    payload: dict[str, Any] | None = None,
    command: str = Query("run"),
    timeout: int = Query(120, ge=1, le=600),
    skip_install: bool = Query(False),
) -> dict[str, Any]:
    """Clone, inspect, and execute a specific module."""
    engine = get_engine()
    mod = engine.registry.get(module_id)
    if not mod:
        raise HTTPException(status_code=404, detail="Module not found")

    result = await engine.runner.run(
        mod,
        command=command,
        env=(payload or {}).get("env"),
        timeout=timeout,
        skip_install=skip_install,
    )
    return {
        "module": module_id,
        "command": command,
        "timeout": timeout,
        "skip_install": skip_install,
        **result,
    }


# ---------- Intel ----------


@app.get("/intel")
async def run_intel(
    report_type: str = Query("trending"),
    min_stars: int = Query(50, ge=0),
) -> dict[str, Any]:
    report = await get_engine().run_intel_scout(report_type, min_stars=min_stars)
    return report.model_dump(mode="json")


# ---------- Dashboard ----------


@app.get("/dashboard/graph-data")
async def graph_data() -> dict[str, Any]:
    """Serve graph data for the React dashboard."""
    engine = get_engine()
    nodes = []
    links = []
    categories = set()
    layers = set()
    eras = set()

    for mod in engine.registry.modules:
        cat = mod.category.value.replace("_", " ").title()
        categories.add(cat)
        layers.add(mod.language or "Unknown")
        eras.add("recent" if mod.updated_at and (mod.updated_at.year >= 2025) else "landmark")
        nodes.append(
            {
                "id": mod.id,
                "name": mod.name,
                "stars": mod.stars,
                "category": cat,
                "layer": mod.language or "Unknown",
                "era": ("recent" if mod.updated_at and (mod.updated_at.year >= 2025) else "landmark"),
                "url": mod.url,
                "description": mod.description or "",
                "language": mod.language or "N/A",
                "why": " | ".join(mod.capabilities) or "Agency module",
            }
        )

    # Simple linking by shared language
    by_lang: dict[str, list[str]] = {}
    for mod in engine.registry.modules:
        lang = mod.language or "Unknown"
        by_lang.setdefault(lang, []).append(mod.id)

    for _lang, ids in by_lang.items():
        for i in range(len(ids)):
            for j in range(i + 1, min(i + 3, len(ids))):
                links.append(
                    {
                        "source": ids[i],
                        "target": ids[j],
                        "type": "related",
                        "strength": 0.5,
                    }
                )

    return {
        "nodes": nodes,
        "links": links,
        "categories": sorted(categories),
        "layers": sorted(layers),
        "eras": sorted(eras),
        "stats": {
            "totalRepos": len(nodes),
            "totalStars": sum(m.stars for m in engine.registry.modules),
            "totalForks": sum(m.forks for m in engine.registry.modules),
            "totalLanguages": len(layers),
        },
    }


# Static dashboard files
static_dir = os.path.join(os.path.dirname(__file__), "../../dashboard/dist")
if os.path.exists(static_dir):
    app.mount(
        "/dashboard/static",
        StaticFiles(directory=os.path.join(static_dir, "assets")),
        name="static",
    )

    @app.get("/dashboard")
    async def dashboard_index() -> FileResponse:
        return FileResponse(os.path.join(static_dir, "index.html"))

    @app.get("/dashboard/{path:path}")
    async def dashboard_spa(path: str) -> FileResponse:
        return FileResponse(os.path.join(static_dir, "index.html"))

else:

    @app.get("/dashboard")
    async def dashboard_not_built() -> dict[str, str]:
        return {"status": "Dashboard not built. Run 'cd dashboard && npm run build'"}
