# OPA Module Marketplace — Design Spec

**Date:** 2026-07-07
**Scope:** Phase 4.1 — Minimal marketplace/catalog for agency modules
**Status:** Approved

---

## Goal

Turn the existing `RepoRegistry` into a browsable, installable marketplace. A module can be discovered, installed globally, and enabled/disabled per project. Later phases will add third-party submissions.

---

## Scope (v1)

- Internal curated catalog sourced from `RepoRegistry`.
- **Install** = clone repo into `data/repos` and mark globally available.
- **Enable** = add module to a project’s active module list.
- **Disable** = remove from project’s active list without deleting files.
- Basic ratings and install counts stored via `AgencyMemory`.
- Dashboard marketplace page with search/filter.
- API endpoints for list, install, enable, disable, rate.
- CLI commands: `opa marketplace`, `opa marketplace install`, `opa marketplace enable/disable`.

Out of scope for v1:
- Payments or paid modules.
- Third-party publisher submissions.
- Versioning or update notifications.
- Dependency resolution between marketplace modules.

---

## Components

### 1. `MarketplaceManager`

**File:** `sahiixx_agency/core/marketplace.py`

Responsibilities:
- List modules from the registry with marketplace metadata overlay.
- Track `install_count`, `average_rating`, `rating_count` per module.
- Manage per-project enabled/disabled module sets.
- Delegate clone/run to existing `RepoRunner` / adapters.

Public methods:
- `list_modules(project_id: str | None = None, query: str = "", category: RepoCategory | None = None) -> list[MarketplaceListing]`
- `install_module(module_id: str) -> MarketplaceListing`
- `enable_module(module_id: str, project_id: str) -> MarketplaceListing`
- `disable_module(module_id: str, project_id: str) -> MarketplaceListing`
- `rate_module(module_id: str, user_id: str, score: float, review: str = "") -> MarketplaceListing`
- `get_module(module_id: str, project_id: str | None = None) -> MarketplaceListing | None`

### 2. Models

**File:** `sahiixx_agency/core/models.py`

```python
class MarketplaceListing(BaseModel):
    module: RepoNode
    install_count: int = 0
    average_rating: float = 0.0
    rating_count: int = 0
    installed_globally: bool = False
    enabled_projects: list[str] = Field(default_factory=list)

class MarketplaceRating(BaseModel):
    id: str
    module_id: str
    user_id: str
    score: float = Field(..., ge=1.0, le=5.0)
    review: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

### 3. Engine Integration

**File:** `sahiixx_agency/core/engine.py`

- Add `self.marketplace = MarketplaceManager(self.registry, self.memory)`.
- Router considers only modules enabled for the current project when a `project_id` is present.
- Default behavior when no `project_id` is provided: all installed modules are eligible (backward compatible).

### 4. API Endpoints

**File:** `sahiixx_agency/api/main.py`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/marketplace` | List modules; query params: `project_id`, `q`, `category` |
| GET | `/marketplace/{module_id}` | Get single module details |
| POST | `/marketplace/{module_id}/install` | Clone and register globally |
| POST | `/marketplace/{module_id}/enable` | Enable for project; query `project_id` |
| POST | `/marketplace/{module_id}/disable` | Disable for project; query `project_id` |
| POST | `/marketplace/{module_id}/rate` | Submit rating; body: `score`, `review`, `user_id` |

### 5. CLI Commands

**File:** `sahiixx_agency/cli/main.py`

- `opa marketplace` — browse listings as a Rich table.
- `opa marketplace install <module-id>` — install a module.
- `opa marketplace enable <module-id> --project <id>` — enable for project.
- `opa marketplace disable <module-id> --project <id>` — disable for project.
- `opa marketplace rate <module-id> <score> [--review "..."]` — rate a module.

### 6. Dashboard Page

**File:** `dashboard/src/pages/Marketplace.tsx`

- Grid of module cards.
- Search bar and category filter.
- Each card shows: name, description, category, stars, install count, rating, risk level, capability badges.
- Buttons: Install / Enable / Disable (state-aware).
- Calls `/api/marketplace` endpoints.

---

## Data Flow

1. Registry sync runs as before (`opa sync` or startup auto-sync).
2. Marketplace lists all `RepoNode`s with marketplace metadata overlay.
3. User installs a module:
   - Clone into `data/repos/{owner}/{name}` via existing `CloneManager`.
   - Mark `installed_globally=true` in marketplace state.
   - Increment `install_count`.
4. User enables a module for a project:
   - Add `project_id` to `enabled_projects`.
   - If not installed globally, auto-install first.
5. Task router filters eligible modules by project enablement when `project_id` is present.
6. Ratings are stored as `marketplace.rating` memory events and aggregated on read.

---

## Storage Keys (AgencyMemory)

- `marketplace:installs:{module_id}` → `{"count": int}`
- `marketplace:ratings:{module_id}` → list of `MarketplaceRating` JSON
- `marketplace:enabled:{project_id}` → list of module IDs

---

## Error Handling

- Install failure (clone fails, repo unreachable) → return error; do not mark installed.
- Enable without install → auto-install first, then enable.
- Disable last enabled module → allow; project has no active marketplace modules.
- Rating out of range or duplicate from same user → 400 validation error.
- Unknown module ID → 404.

---

## Security Considerations

- Marketplace install must respect `NetworkPolicy` and `DependencyScanner` gates (already enforced by `RepoRunner`).
- Ratings should be attributed to a user/tenant to prevent spam (v1 uses simple `user_id`).
- No unauthenticated submissions in v1.

---

## Testing

- `tests/test_marketplace.py` — unit tests for `MarketplaceManager`.
- `tests/test_api_marketplace.py` — API endpoint tests.
- `tests/test_cli_marketplace.py` — CLI command tests.
- Dashboard build must succeed after adding `Marketplace.tsx`.
- Full `pytest tests/` must remain green.

---

## Migration / Rollout

- Marketplace is additive; existing registry and routing behavior remain unchanged.
- When no `project_id` is supplied, all installed modules are eligible (backward compatible).
- Project enablement becomes relevant once clients start passing `project_id` in dispatch.

---

## Future Work (Phase 4.x)

- Third-party publisher submissions and review queue.
- Paid modules and license keys.
- Module update notifications and version management.
- Marketplace analytics for publishers.
