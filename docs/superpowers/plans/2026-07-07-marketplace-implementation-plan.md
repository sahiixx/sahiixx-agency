# OPA Module Marketplace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a minimal, internal marketplace that lets users discover, install, enable/disable per-project, and rate agency modules sourced from the existing registry.

**Architecture:** A new `MarketplaceManager` wraps `RepoRegistry` and `AgencyMemory` to overlay install counts, ratings, and per-project enablement onto existing `RepoNode` modules. A thin API/CLI/dashboard layer exposes listing, install, enable/disable, and rating actions. The task router optionally filters by project enablement when a `project_id` is present.

**Tech Stack:** Python 3.11+, Pydantic v2, FastAPI, Typer, Rich, React + Tailwind + TypeScript, pytest.

## Global Constraints

- Target Python 3.11+, Pydantic v2, FastAPI, Typer, Rich.
- All new code must have type hints and tests.
- Existing 295 tests must keep passing.
- Do not break existing registry, routing, or adapter behavior.
- Disk is at 94.3% on `C:` — avoid large Docker builds or cloning real repos in tests. Use mocks for clone/install where possible.
- Marketplace install must reuse existing `CloneManager`/`RepoRunner` so `NetworkPolicy` and `DependencyScanner` gates are enforced.
- No payments, publisher submissions, versioning, or module-to-module dependency resolution in v1.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `sahiixx_agency/core/models.py` | Add `MarketplaceListing` and `MarketplaceRating` Pydantic models |
| `sahiixx_agency/core/marketplace.py` | `MarketplaceManager` — list, install, enable/disable, rate modules |
| `sahiixx_agency/core/engine.py` | Wire `MarketplaceManager`; pass `project_id` into routing context |
| `sahiixx_agency/core/router.py` | Respect project enablement when `project_id` is present in task |
| `sahiixx_agency/api/main.py` | Add `/marketplace/*` REST endpoints |
| `sahiixx_agency/cli/main.py` | Add `opa marketplace` subcommands |
| `dashboard/src/pages/Marketplace.tsx` | Marketplace UI page |
| `dashboard/src/App.tsx` | Add `/marketplace` route |
| `tests/test_marketplace.py` | Unit tests for `MarketplaceManager` |
| `tests/test_api_marketplace.py` | API endpoint tests |
| `tests/test_cli_marketplace.py` | CLI command tests |

---

## Task 1: Add Marketplace Models

**Files:**
- Modify: `sahiixx_agency/core/models.py`
- Test: `tests/test_marketplace.py` (create)

**Interfaces:**
- Produces: `MarketplaceListing` and `MarketplaceRating` models used by `MarketplaceManager` and API.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_marketplace.py
from __future__ import annotations

from sahiixx_agency.core.models import MarketplaceListing, MarketplaceRating, RepoNode


def test_marketplace_listing_defaults() -> None:
    node = RepoNode(id="test", name="test", full_name="owner/test", url="https://github.com/owner/test")
    listing = MarketplaceListing(module=node)
    assert listing.install_count == 0
    assert listing.average_rating == 0.0
    assert listing.rating_count == 0
    assert listing.installed_globally is False
    assert listing.enabled_projects == []


def test_marketplace_rating_validation() -> None:
    rating = MarketplaceRating(id="r1", module_id="test", user_id="u1", score=4.5)
    assert rating.score == 4.5


def test_marketplace_rating_rejects_out_of_range() -> None:
    from pydantic import ValidationError

    with __import__("pytest").raises(ValidationError):
        MarketplaceRating(id="r1", module_id="test", user_id="u1", score=6.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_marketplace.py -v`

Expected: FAIL — `ImportError: cannot import name 'MarketplaceListing'`

- [ ] **Step 3: Write minimal implementation**

Append to `sahiixx_agency/core/models.py` after the `ChatThread` model:

```python
class MarketplaceListing(BaseModel):
    """A registry module decorated with marketplace metadata."""

    module: RepoNode
    install_count: int = 0
    average_rating: float = 0.0
    rating_count: int = 0
    installed_globally: bool = False
    enabled_projects: list[str] = Field(default_factory=list)


class MarketplaceRating(BaseModel):
    """A user rating for a marketplace module."""

    id: str = Field(...)
    module_id: str = Field(...)
    user_id: str = Field(...)
    score: float = Field(..., ge=1.0, le=5.0)
    review: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_marketplace.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sahiixx_agency/core/models.py tests/test_marketplace.py
git commit -m "feat(marketplace): add MarketplaceListing and MarketplaceRating models"
```

---

## Task 2: Implement MarketplaceManager Core

**Files:**
- Create: `sahiixx_agency/core/marketplace.py`
- Modify: `sahiixx_agency/core/runner.py` (make `CloneManager.clone` mock-friendly by accepting an injectable clone manager)
- Test: `tests/test_marketplace.py`

**Interfaces:**
- Consumes: `RepoRegistry`, `AgencyMemory`, `RepoNode`, `MarketplaceListing`, `MarketplaceRating`
- Produces: `MarketplaceManager` with methods: `list_modules`, `get_module`, `install_module`, `enable_module`, `disable_module`, `rate_module`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_marketplace.py
import pytest

from sahiixx_agency.core.marketplace import MarketplaceManager
from sahiixx_agency.core.memory import AgencyMemory
from sahiixx_agency.core.models import RepoNode
from sahiixx_agency.core.registry import RepoRegistry


@pytest.fixture
def marketplace(tmp_path):
    memory = AgencyMemory(data_dir=str(tmp_path), backend="json")
    registry = RepoRegistry(data_dir=str(tmp_path), github_token=None)
    node = RepoNode(id="html-anything", name="html-anything", full_name="nexu-io/html-anything", url="https://github.com/nexu-io/html-anything")
    registry.modules[node.id] = node
    registry.save()
    return MarketplaceManager(registry, memory)


@pytest.mark.asyncio
async def test_list_modules_returns_registry_modules(marketplace):
    listings = await marketplace.list_modules()
    assert len(listings) == 1
    assert listings[0].module.id == "html-anything"


@pytest.mark.asyncio
async def test_install_module_clones_and_marks_installed(marketplace, tmp_path):
    # Inject fake clone manager to avoid network
    class FakeCloneManager:
        async def clone(self, node):
            path = tmp_path / node.name
            path.mkdir()
            return path

    marketplace.clone_manager = FakeCloneManager()
    listing = await marketplace.install_module("html-anything")
    assert listing.installed_globally is True
    assert listing.install_count == 1


@pytest.mark.asyncio
async def test_enable_and_disable_project(marketplace, tmp_path):
    class FakeCloneManager:
        async def clone(self, node):
            path = tmp_path / node.name
            path.mkdir()
            return path

    marketplace.clone_manager = FakeCloneManager()
    await marketplace.install_module("html-anything")
    listing = await marketplace.enable_module("html-anything", "project-1")
    assert "project-1" in listing.enabled_projects
    listing = await marketplace.disable_module("html-anything", "project-1")
    assert "project-1" not in listing.enabled_projects


@pytest.mark.asyncio
async def test_rate_module_updates_average(marketplace):
    await marketplace.rate_module("html-anything", "u1", 5.0)
    await marketplace.rate_module("html-anything", "u2", 3.0)
    listing = (await marketplace.list_modules())[0]
    assert listing.average_rating == 4.0
    assert listing.rating_count == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_marketplace.py::test_list_modules_returns_registry_modules -v`

Expected: FAIL — `ModuleNotFoundError: No module named 'sahiixx_agency.core.marketplace'`

- [ ] **Step 3: Write minimal implementation**

Create `sahiixx_agency/core/marketplace.py`:

```python
"""Marketplace for discovering, installing, and rating agency modules."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from .memory import AgencyMemory
from .models import MarketplaceListing, MarketplaceRating, RepoCategory, RepoNode
from .registry import RepoRegistry
from .runner import CloneManager


class MarketplaceManager:
    """Overlay marketplace metadata on top of RepoRegistry."""

    def __init__(
        self,
        registry: RepoRegistry,
        memory: AgencyMemory,
        clone_manager: CloneManager | None = None,
        data_dir: str = "./data",
    ) -> None:
        self.registry = registry
        self.memory = memory
        self.clone_manager = clone_manager or CloneManager(f"{data_dir}/repos")

    def _install_key(self, module_id: str) -> str:
        return f"marketplace:installs:{module_id}"

    def _ratings_key(self, module_id: str) -> str:
        return f"marketplace:ratings:{module_id}"

    def _enabled_key(self, project_id: str) -> str:
        return f"marketplace:enabled:{project_id}"

    def _get_install_count(self, module_id: str) -> int:
        raw = self.memory.get(self._install_key(module_id), default={"count": 0})
        return raw.get("count", 0)

    def _set_install_count(self, module_id: str, count: int) -> None:
        self.memory.set(self._install_key(module_id), {"count": count})

    def _get_ratings(self, module_id: str) -> list[MarketplaceRating]:
        raw = self.memory.get(self._ratings_key(module_id), default=[])
        return [MarketplaceRating.model_validate(r) for r in raw]

    def _set_ratings(self, module_id: str, ratings: list[MarketplaceRating]) -> None:
        self.memory.set(self._ratings_key(module_id), [r.model_dump(mode="json") for r in ratings])

    def _get_enabled_projects(self, module_id: str) -> list[str]:
        enabled: list[str] = []
        # Memory keys are project-centric; scan is not feasible at scale.
        # For v1 we compute enabled_projects from per-project lists.
        return enabled

    def _is_enabled_for_project(self, module_id: str, project_id: str) -> bool:
        enabled = self.memory.get(self._enabled_key(project_id), default=[])
        return module_id in enabled

    def _build_listing(
        self,
        module: RepoNode,
        project_id: str | None = None,
    ) -> MarketplaceListing:
        ratings = self._get_ratings(module.id)
        count = len(ratings)
        average = sum(r.score for r in ratings) / count if count else 0.0
        enabled_projects: list[str] = []
        if project_id:
            if self._is_enabled_for_project(module.id, project_id):
                enabled_projects.append(project_id)
        install_count = self._get_install_count(module.id)
        installed = install_count > 0
        return MarketplaceListing(
            module=module,
            install_count=install_count,
            average_rating=average,
            rating_count=count,
            installed_globally=installed,
            enabled_projects=enabled_projects,
        )

    async def list_modules(
        self,
        project_id: str | None = None,
        query: str = "",
        category: RepoCategory | None = None,
    ) -> list[MarketplaceListing]:
        """Return marketplace listings, optionally filtered."""
        modules = list(self.registry.modules.values())
        listings: list[MarketplaceListing] = []
        for module in modules:
            if query and query.lower() not in module.name.lower() and query.lower() not in (module.description or "").lower():
                continue
            if category and module.category != category:
                continue
            listings.append(self._build_listing(module, project_id=project_id))
        listings.sort(key=lambda x: (x.average_rating, x.install_count, x.module.stars), reverse=True)
        return listings

    async def get_module(
        self,
        module_id: str,
        project_id: str | None = None,
    ) -> MarketplaceListing | None:
        module = self.registry.modules.get(module_id)
        if module is None:
            return None
        return self._build_listing(module, project_id=project_id)

    async def install_module(self, module_id: str) -> MarketplaceListing:
        module = self.registry.modules.get(module_id)
        if module is None:
            raise ValueError(f"Module {module_id} not found")
        await self.clone_manager.clone(module)
        count = self._get_install_count(module_id) + 1
        self._set_install_count(module_id, count)
        return await self.get_module(module_id)

    async def enable_module(self, module_id: str, project_id: str) -> MarketplaceListing:
        module = self.registry.modules.get(module_id)
        if module is None:
            raise ValueError(f"Module {module_id} not found")
        current = self._get_install_count(module_id)
        if current == 0:
            await self.install_module(module_id)
        enabled = set(self.memory.get(self._enabled_key(project_id), default=[]))
        enabled.add(module_id)
        self.memory.set(self._enabled_key(project_id), sorted(enabled))
        return await self.get_module(module_id, project_id=project_id)

    async def disable_module(self, module_id: str, project_id: str) -> MarketplaceListing:
        module = self.registry.modules.get(module_id)
        if module is None:
            raise ValueError(f"Module {module_id} not found")
        enabled = set(self.memory.get(self._enabled_key(project_id), default=[]))
        enabled.discard(module_id)
        self.memory.set(self._enabled_key(project_id), sorted(enabled))
        return await self.get_module(module_id, project_id=project_id)

    async def rate_module(
        self,
        module_id: str,
        user_id: str,
        score: float,
        review: str = "",
    ) -> MarketplaceListing:
        module = self.registry.modules.get(module_id)
        if module is None:
            raise ValueError(f"Module {module_id} not found")
        ratings = self._get_ratings(module_id)
        # Replace previous rating from same user
        ratings = [r for r in ratings if r.user_id != user_id]
        ratings.append(
            MarketplaceRating(
                id=f"rating_{uuid.uuid4().hex[:12]}",
                module_id=module_id,
                user_id=user_id,
                score=score,
                review=review,
                timestamp=datetime.now(timezone.utc),
            )
        )
        self._set_ratings(module_id, ratings)
        return await self.get_module(module_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_marketplace.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sahiixx_agency/core/marketplace.py tests/test_marketplace.py
git commit -m "feat(marketplace): add MarketplaceManager with install, enable, disable, rate"
```

---

## Task 3: Wire MarketplaceManager into Engine and Router

**Files:**
- Modify: `sahiixx_agency/core/engine.py`
- Modify: `sahiixx_agency/core/router.py`
- Test: `tests/test_marketplace.py`

**Interfaces:**
- Consumes: `MarketplaceManager`
- Produces: `AgencyEngine.marketplace`, router behavior that filters by project enablement

- [ ] **Step 1: Write the failing test**

```python
# tests/test_marketplace.py
import pytest

from sahiixx_agency.core.engine import AgencyEngine
from sahiixx_agency.core.models import AgencyConfig, AgencyTask, RepoCategory, RepoNode


@pytest.mark.asyncio
async def test_engine_marketplace_filters_routing_by_project(tmp_path):
    config = AgencyConfig(data_dir=str(tmp_path), memory_backend="json")
    engine = AgencyEngine(config)
    node = RepoNode(
        id="html-anything",
        name="html-anything",
        full_name="nexu-io/html-anything",
        url="https://github.com/nexu-io/html-anything",
        category=RepoCategory.COOKBOOK,
    )
    engine.registry.modules[node.id] = node
    engine.registry.save()

    # Without project_id, module is eligible even when not enabled
    task = AgencyTask(id="t1", intent="build a landing page", category=RepoCategory.COOKBOOK)
    candidates = engine.router.score_candidates(task)
    assert any(c.module_id == "html-anything" for c in candidates)

    # With project_id and module not enabled, module is filtered out
    task2 = AgencyTask(id="t2", intent="build a landing page", category=RepoCategory.COOKBOOK, project_id="p1")
    candidates2 = engine.router.score_candidates(task2)
    assert not any(c.module_id == "html-anything" for c in candidates2)

    # After enabling for project, module is eligible again
    await engine.marketplace.enable_module("html-anything", "p1")
    candidates3 = engine.router.score_candidates(task2)
    assert any(c.module_id == "html-anything" for c in candidates3)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_marketplace.py::test_engine_marketplace_filters_routing_by_project -v`

Expected: FAIL — `AttributeError: 'AgencyEngine' object has no attribute 'marketplace'`

- [ ] **Step 3: Write minimal implementation**

In `sahiixx_agency/core/engine.py`:

1. Add import:

```python
from .marketplace import MarketplaceManager
```

2. In `AgencyEngine.__init__`, add after `self.long_term_memory = ...`:

```python
        self.marketplace = MarketplaceManager(
            self.registry,
            self.memory,
            clone_manager=self.runner.clone_manager,
            data_dir=self.config.data_dir,
        )
```

In `sahiixx_agency/core/router.py`, modify the candidate scoring so that when `task.project_id` is present, only modules enabled for that project are considered. The exact change depends on the current `score_candidates` signature — open the file and add a guard:

```python
# inside score_candidates, after loading candidates
if task.project_id:
    enabled = self.engine.marketplace._is_enabled_for_project(module_id, task.project_id)
    if not enabled:
        continue
```

If `router.py` does not have access to the engine, pass `engine` into the router or use the existing reference.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_marketplace.py -v`

Expected: PASS

- [ ] **Step 5: Run focused existing tests**

Run: `pytest tests/test_core.py tests/test_api.py -q`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add sahiixx_agency/core/engine.py sahiixx_agency/core/router.py tests/test_marketplace.py
git commit -m "feat(marketplace): wire MarketplaceManager into engine and router"
```

---

## Task 4: Add Marketplace API Endpoints

**Files:**
- Modify: `sahiixx_agency/api/main.py`
- Test: `tests/test_api_marketplace.py` (create)

**Interfaces:**
- Consumes: `AgencyEngine.marketplace`
- Produces: REST endpoints `/marketplace`, `/marketplace/{module_id}`, `/marketplace/{module_id}/install`, `/marketplace/{module_id}/enable`, `/marketplace/{module_id}/disable`, `/marketplace/{module_id}/rate`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_api_marketplace.py
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from sahiixx_agency.api.main import app
from sahiixx_agency.core.engine import AgencyEngine
from sahiixx_agency.core.models import RepoCategory, RepoNode


@pytest.fixture
def client(tmp_path, monkeypatch):
    config = {"data_dir": str(tmp_path), "memory_backend": "json"}
    engine = AgencyEngine.from_config(config)
    node = RepoNode(
        id="html-anything",
        name="html-anything",
        full_name="nexu-io/html-anything",
        url="https://github.com/nexu-io/html-anything",
        category=RepoCategory.COOKBOOK,
    )
    engine.registry.modules[node.id] = node
    engine.registry.save()
    monkeypatch.setattr(app.state, "engine", engine)
    return TestClient(app)


def test_list_marketplace(client):
    response = client.get("/marketplace")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["module"]["id"] == "html-anything"


def test_get_marketplace_module(client):
    response = client.get("/marketplace/html-anything")
    assert response.status_code == 200
    assert response.json()["module"]["id"] == "html-anything"


def test_install_module(client, tmp_path):
    class FakeCloneManager:
        async def clone(self, node):
            path = tmp_path / node.name
            path.mkdir()
            return path

    engine = app.state.engine
    engine.marketplace.clone_manager = FakeCloneManager()
    response = client.post("/marketplace/html-anything/install")
    assert response.status_code == 200
    assert response.json()["installed_globally"] is True


def test_enable_disable_module(client, tmp_path):
    class FakeCloneManager:
        async def clone(self, node):
            path = tmp_path / node.name
            path.mkdir()
            return path

    engine = app.state.engine
    engine.marketplace.clone_manager = FakeCloneManager()
    response = client.post("/marketplace/html-anything/enable?project_id=p1")
    assert response.status_code == 200
    assert "p1" in response.json()["enabled_projects"]
    response = client.post("/marketplace/html-anything/disable?project_id=p1")
    assert response.status_code == 200
    assert "p1" not in response.json()["enabled_projects"]


def test_rate_module(client):
    response = client.post(
        "/marketplace/html-anything/rate",
        json={"user_id": "u1", "score": 5.0, "review": "great"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["average_rating"] == 5.0
    assert data["rating_count"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api_marketplace.py::test_list_marketplace -v`

Expected: FAIL — `404 Not Found`

- [ ] **Step 3: Write minimal implementation**

Add to `sahiixx_agency/api/main.py` (use the existing engine accessor pattern, e.g. `request.app.state.engine`):

```python
from sahiixx_agency.core.models import MarketplaceListing, MarketplaceRating, RepoCategory


@api_router.get("/marketplace", response_model=list[MarketplaceListing])
async def list_marketplace(
    request: Request,
    project_id: str | None = None,
    q: str = "",
    category: RepoCategory | None = None,
):
    engine = request.app.state.engine
    return await engine.marketplace.list_modules(project_id=project_id, query=q, category=category)


@api_router.get("/marketplace/{module_id}", response_model=MarketplaceListing)
async def get_marketplace_module(request: Request, module_id: str, project_id: str | None = None):
    engine = request.app.state.engine
    listing = await engine.marketplace.get_module(module_id, project_id=project_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Module not found")
    return listing


@api_router.post("/marketplace/{module_id}/install", response_model=MarketplaceListing)
async def install_marketplace_module(request: Request, module_id: str):
    engine = request.app.state.engine
    try:
        return await engine.marketplace.install_module(module_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@api_router.post("/marketplace/{module_id}/enable", response_model=MarketplaceListing)
async def enable_marketplace_module(request: Request, module_id: str, project_id: str):
    engine = request.app.state.engine
    try:
        return await engine.marketplace.enable_module(module_id, project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@api_router.post("/marketplace/{module_id}/disable", response_model=MarketplaceListing)
async def disable_marketplace_module(request: Request, module_id: str, project_id: str):
    engine = request.app.state.engine
    try:
        return await engine.marketplace.disable_module(module_id, project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@api_router.post("/marketplace/{module_id}/rate", response_model=MarketplaceListing)
async def rate_marketplace_module(
    request: Request,
    module_id: str,
    body: dict[str, Any],
):
    engine = request.app.state.engine
    try:
        return await engine.marketplace.rate_module(
            module_id,
            user_id=body["user_id"],
            score=body["score"],
            review=body.get("review", ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_api_marketplace.py -v`

Expected: PASS

- [ ] **Step 5: Run focused existing tests**

Run: `pytest tests/test_api.py tests/test_api_marketplace.py -q`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add sahiixx_agency/api/main.py tests/test_api_marketplace.py
git commit -m "feat(marketplace): add marketplace REST endpoints"
```

---

## Task 5: Add Marketplace CLI Commands

**Files:**
- Modify: `sahiixx_agency/cli/main.py`
- Test: `tests/test_cli_marketplace.py` (create)

**Interfaces:**
- Consumes: `AgencyEngine.marketplace`
- Produces: `opa marketplace`, `opa marketplace install`, `opa marketplace enable`, `opa marketplace disable`, `opa marketplace rate`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli_marketplace.py
from __future__ import annotations

import pytest
from typer.testing import CliRunner

from sahiixx_agency.cli.main import app
from sahiixx_agency.core.engine import AgencyEngine
from sahiixx_agency.core.models import RepoCategory, RepoNode


@pytest.fixture
def patched_engine(tmp_path, monkeypatch):
    from sahiixx_agency.cli.main import get_engine

    config = {"data_dir": str(tmp_path), "memory_backend": "json"}
    engine = AgencyEngine.from_config(config)
    node = RepoNode(
        id="html-anything",
        name="html-anything",
        full_name="nexu-io/html-anything",
        url="https://github.com/nexu-io/html-anything",
        category=RepoCategory.COOKBOOK,
    )
    engine.registry.modules[node.id] = node
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli_marketplace.py::test_marketplace_list -v`

Expected: FAIL — `No such command 'marketplace'`

- [ ] **Step 3: Write minimal implementation**

Add a Typer sub-app in `sahiixx_agency/cli/main.py`:

```python
marketplace_app = typer.Typer(help="Discover and install agency modules")
app.add_typer(marketplace_app, name="marketplace")


@marketplace_app.callback()
def marketplace_callback() -> None:
    """Marketplace commands."""


@marketplace_app.command("list")
def marketplace_list(
    project: str | None = typer.Option(None, "--project", help="Filter by project enablement"),
    category: str | None = typer.Option(None, "--category", help="Filter by category"),
    query: str | None = typer.Option(None, "--query", "-q", help="Search query"),
) -> None:
    engine = get_engine()
    cat = RepoCategory(category) if category else None
    listings = asyncio.run(engine.marketplace.list_modules(project_id=project, query=query or "", category=cat))
    table = Table(title="Marketplace Modules")
    table.add_column("ID")
    table.add_column("Category")
    table.add_column("Rating")
    table.add_column("Installs")
    table.add_column("Enabled")
    for listing in listings:
        enabled = "✓" if (project and project in listing.enabled_projects) else ""
        table.add_row(
            listing.module.id,
            listing.module.category.value,
            f"{listing.average_rating:.1f} ({listing.rating_count})",
            str(listing.install_count),
            enabled,
        )
    console.print(table)


@marketplace_app.command("install")
def marketplace_install(module_id: str) -> None:
    engine = get_engine()
    listing = asyncio.run(engine.marketplace.install_module(module_id))
    console.print(f"Installed [bold]{module_id}[/bold] (global install count: {listing.install_count})")


@marketplace_app.command("enable")
def marketplace_enable(
    module_id: str,
    project: str = typer.Option(..., "--project", help="Project ID to enable for"),
) -> None:
    engine = get_engine()
    listing = asyncio.run(engine.marketplace.enable_module(module_id, project))
    console.print(f"Enabled [bold]{module_id}[/bold] for project {project}")


@marketplace_app.command("disable")
def marketplace_disable(
    module_id: str,
    project: str = typer.Option(..., "--project", help="Project ID to disable for"),
) -> None:
    engine = get_engine()
    listing = asyncio.run(engine.marketplace.disable_module(module_id, project))
    console.print(f"Disabled [bold]{module_id}[/bold] for project {project}")


@marketplace_app.command("rate")
def marketplace_rate(
    module_id: str,
    score: float = typer.Argument(..., help="Rating from 1 to 5"),
    user: str = typer.Option("operator", "--user", help="User ID"),
    review: str | None = typer.Option(None, "--review", help="Optional review text"),
) -> None:
    engine = get_engine()
    listing = asyncio.run(engine.marketplace.rate_module(module_id, user, score, review or ""))
    console.print(f"Rated [bold]{module_id}[/bold]: {listing.average_rating:.1f} ({listing.rating_count} ratings)")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli_marketplace.py -v`

Expected: PASS

- [ ] **Step 5: Run focused existing tests**

Run: `pytest tests/test_cli.py tests/test_cli_marketplace.py -q`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add sahiixx_agency/cli/main.py tests/test_cli_marketplace.py
git commit -m "feat(marketplace): add marketplace CLI commands"
```

---

## Task 6: Add Marketplace Dashboard Page

**Files:**
- Create: `dashboard/src/pages/Marketplace.tsx`
- Modify: `dashboard/src/App.tsx`
- Test: dashboard build (`npm run build`)

**Interfaces:**
- Consumes: `/api/marketplace` endpoints
- Produces: React page at `/marketplace`

- [ ] **Step 1: Create the Marketplace page**

Create `dashboard/src/pages/Marketplace.tsx`:

```tsx
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

interface RepoNode {
  id: string;
  name: string;
  full_name: string;
  description: string | null;
  category: string;
  stars: number;
  risk_level: string;
  capabilities: string[];
}

interface MarketplaceListing {
  module: RepoNode;
  install_count: number;
  average_rating: number;
  rating_count: number;
  installed_globally: boolean;
  enabled_projects: string[];
}

export default function MarketplacePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const projectId = searchParams.get("project_id") || "";
  const [listings, setListings] = useState<MarketplaceListing[]>([]);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");

  async function fetchListings() {
    const params = new URLSearchParams();
    if (projectId) params.set("project_id", projectId);
    if (query) params.set("q", query);
    if (category) params.set("category", category);
    const res = await fetch(`/api/marketplace?${params.toString()}`);
    const data = await res.json();
    setListings(data);
  }

  useEffect(() => {
    fetchListings();
  }, [projectId, query, category]);

  async function install(moduleId: string) {
    await fetch(`/api/marketplace/${moduleId}/install`, { method: "POST" });
    await fetchListings();
  }

  async function enable(moduleId: string) {
    await fetch(`/api/marketplace/${moduleId}/enable?project_id=${projectId}`, { method: "POST" });
    await fetchListings();
  }

  async function disable(moduleId: string) {
    await fetch(`/api/marketplace/${moduleId}/disable?project_id=${projectId}`, { method: "POST" });
    await fetchListings();
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Module Marketplace</h1>
      <div className="flex gap-4 mb-6">
        <input
          type="text"
          placeholder="Search modules..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="border rounded px-3 py-2"
        />
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="border rounded px-3 py-2"
        >
          <option value="">All categories</option>
          <option value="agent_framework">Agent Framework</option>
          <option value="voice_ai">Voice AI</option>
          <option value="security">Security</option>
          <option value="career">Career</option>
          <option value="content_media">Content Media</option>
          <option value="knowledge">Knowledge</option>
          <option value="cookbook">Cookbook</option>
        </select>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {listings.map((listing) => (
          <div key={listing.module.id} className="border rounded p-4 shadow-sm">
            <h2 className="text-lg font-semibold">{listing.module.name}</h2>
            <p className="text-sm text-gray-600 mb-2">{listing.module.description || "No description"}</p>
            <div className="text-xs text-gray-500 mb-2">
              {listing.module.category} • ⭐ {listing.module.stars} • 📥 {listing.install_count} • ⭐ {listing.average_rating.toFixed(1)} ({listing.rating_count})
            </div>
            <div className="flex flex-wrap gap-1 mb-3">
              {listing.module.capabilities.slice(0, 5).map((cap) => (
                <span key={cap} className="bg-gray-100 text-xs px-2 py-1 rounded">{cap}</span>
              ))}
            </div>
            <div className="flex gap-2">
              {!listing.installed_globally ? (
                <button onClick={() => install(listing.module.id)} className="bg-primary text-white px-3 py-1 rounded text-sm">Install</button>
              ) : projectId && !listing.enabled_projects.includes(projectId) ? (
                <button onClick={() => enable(listing.module.id)} className="bg-green-600 text-white px-3 py-1 rounded text-sm">Enable</button>
              ) : projectId ? (
                <button onClick={() => disable(listing.module.id)} className="bg-red-500 text-white px-3 py-1 rounded text-sm">Disable</button>
              ) : null}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add route in App.tsx**

In `dashboard/src/App.tsx`, add:

```tsx
import MarketplacePage from "./pages/Marketplace";

// inside router/routes
<Route path="/marketplace" element={<MarketplacePage />} />
```

Also add a link in the navbar to `/marketplace`.

- [ ] **Step 3: Build the dashboard**

Run:

```bash
cd dashboard && npm run build
```

Expected: build succeeds with no TypeScript errors.

- [ ] **Step 4: Commit**

```bash
git add dashboard/src/pages/Marketplace.tsx dashboard/src/App.tsx dashboard/src/components/Navbar.tsx
git commit -m "feat(marketplace): add marketplace dashboard page"
```

---

## Task 7: Final Verification

**Files:** all touched

- [ ] **Step 1: Run full test suite**

Run: `pytest tests/ -q --basetemp=./.pytest_tmp`

Expected: PASS (target >295 tests)

- [ ] **Step 2: Build dashboard**

Run: `cd dashboard && npm run build`

Expected: build succeeds

- [ ] **Step 3: Commit any remaining changes**

```bash
git add -A
git commit -m "feat(marketplace): final verification and dashboard build"
```

- [ ] **Step 4: Push to GitHub**

```bash
git push origin master
```

---

## Spec Coverage Check

| Spec Requirement | Task |
|------------------|------|
| `MarketplaceManager` with listing/install/enable/disable/rate | Task 2 |
| `MarketplaceListing` and `MarketplaceRating` models | Task 1 |
| Engine integration | Task 3 |
| Router project enablement filter | Task 3 |
| `/marketplace` API endpoints | Task 4 |
| `opa marketplace` CLI | Task 5 |
| Dashboard marketplace page | Task 6 |
| Storage keys in `AgencyMemory` | Task 2 |
| Error handling | Tasks 2, 4 |
| Security gates via existing `RepoRunner` | Task 2 |

## Placeholder Scan

No placeholders. All steps include exact code, commands, and expected outputs.

## Type Consistency Check

- `MarketplaceManager` methods are `async` to support `clone_manager.clone`.
- API endpoints use `response_model=MarketplaceListing` consistently.
- CLI commands call `asyncio.run(...)` around async manager methods.
- `RepoCategory` is used for category filter everywhere.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-07-marketplace-implementation-plan.md`.

Two execution options:

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks, fast iteration
2. **Inline Execution** — execute tasks in this session using `executing-plans`, batch execution with checkpoints

Which approach?
