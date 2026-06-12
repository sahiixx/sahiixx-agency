"""FastAPI server for the One Person Agency."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from sahiixx_agency.core.engine import AgencyEngine
from sahiixx_agency.core.models import AgencyConfig, RepoCategory

_engine: AgencyEngine | None = None


def get_engine() -> AgencyEngine:
    if _engine is None:
        raise RuntimeError("Engine not initialized")
    return _engine


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
    await _engine.start_worker()
    # Auto-sync on startup if registry is empty
    if not _engine.registry.modules:
        await _engine.sync_repos(config.github_username)
    yield
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
async def health(engine: Annotated[AgencyEngine, Depends(get_engine)]) -> dict[str, Any]:
    return {"status": "healthy", "registry_count": len(engine.registry.modules)}


@app.get("/stats")
async def stats(engine: Annotated[AgencyEngine, Depends(get_engine)]) -> dict[str, Any]:
    return engine.stats()


# ---------- Registry ----------


@app.get("/registry")
async def list_registry(
    engine: Annotated[AgencyEngine, Depends(get_engine)],
    category: str | None = Query(None),
    language: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[dict[str, Any]]:
    modules = engine.registry.modules
    if category:
        try:
            cat = RepoCategory(category)
            modules = [m for m in modules if m.category == cat]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown category: {category}") from None
    if language:
        modules = [m for m in modules if m.language and m.language.lower() == language.lower()]
    modules.sort(key=lambda m: m.stars, reverse=True)
    return [m.model_dump(mode="json") for m in modules[offset : offset + limit]]


@app.get("/registry/{module_id}")
async def get_module(module_id: str, engine: Annotated[AgencyEngine, Depends(get_engine)]) -> dict[str, Any]:
    mod = engine.registry.get(module_id)
    if not mod:
        raise HTTPException(status_code=404, detail="Module not found")
    return mod.model_dump(mode="json")


@app.post("/registry/sync")
async def sync_registry(
    engine: Annotated[AgencyEngine, Depends(get_engine)],
    username: str | None = Query(None),
) -> dict[str, Any]:
    discovered = await engine.sync_repos(username or engine.config.github_username)
    return {"synced": len(discovered), "username": username or engine.config.github_username}


# ---------- Tasks ----------


@app.post("/tasks")
async def create_task(
    intent: str,
    engine: Annotated[AgencyEngine, Depends(get_engine)],
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    task = await engine.dispatch(intent, payload)
    return task.model_dump(mode="json")


@app.get("/tasks")
async def list_tasks(
    engine: Annotated[AgencyEngine, Depends(get_engine)],
    limit: int = Query(50, ge=1, le=200),
) -> list[dict[str, Any]]:
    tasks = engine.list_tasks(limit=limit)
    return [t.model_dump(mode="json") for t in tasks]


@app.post("/tasks/{module_id:path}/execute")
async def execute_module(
    module_id: str,
    engine: Annotated[AgencyEngine, Depends(get_engine)],
    payload: dict[str, Any] | None = None,
    command: str = Query("run"),
    timeout: int = Query(120, ge=1, le=600),
) -> dict[str, Any]:
    """Clone, inspect, and execute a specific module."""
    mod = engine.registry.get(module_id)
    if not mod:
        raise HTTPException(status_code=404, detail="Module not found")

    result = await engine.runner.run(
        mod,
        command=command,
        env=(payload or {}).get("env"),
        timeout=timeout,
    )
    return {
        "module": module_id,
        "command": command,
        "timeout": timeout,
        **result,
    }


@app.get("/tasks/{task_id}")
async def get_task(task_id: str, engine: Annotated[AgencyEngine, Depends(get_engine)]) -> dict[str, Any]:
    task = engine.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.model_dump(mode="json")


# ---------- Intel ----------


@app.get("/intel")
async def run_intel(
    engine: Annotated[AgencyEngine, Depends(get_engine)],
    report_type: str = Query("trending"),
    min_stars: int = Query(50, ge=0),
) -> dict[str, Any]:
    report = await engine.run_intel_scout(report_type, min_stars=min_stars)
    return report.model_dump(mode="json")


# ---------- Dashboard ----------


@app.get("/dashboard/graph-data")
async def graph_data(engine: Annotated[AgencyEngine, Depends(get_engine)]) -> dict[str, Any]:
    """Serve graph data for the React dashboard."""
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
                "era": "recent" if mod.updated_at and (mod.updated_at.year >= 2025) else "landmark",
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
    app.mount("/dashboard/static", StaticFiles(directory=os.path.join(static_dir, "assets")), name="static")

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
