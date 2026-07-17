# Portfolio Auto-Publish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When a new module appears in OPA's registry, automatically draft a curated portfolio entry, insert it into the portfolio site's `src/data.ts`, build, deploy to Cloudflare Pages, and notify the outcome.

**Architecture:** `sync_repos()` diffs the registry and publishes `registry.module_added` on the bus → the existing event-workflow plumbing fires `data/workflows/portfolio-publisher.json` → its dispatch step routes to a new `PortfolioPublisherAdapter` (specialized adapter) that gates, LLM-drafts a `Project` entry, inserts it at a marker in `src/data.ts`, then builds → commits → deploys → pushes → notifies.

**Tech Stack:** Python 3.11+ (pydantic v2, pytest + pytest-asyncio), existing LLMManager / NotificationManager / MessageBus; TypeScript data file edit by string insertion; npm/vite build; wrangler Pages deploy via subprocess.

**Spec:** `docs/superpowers/specs/2026-07-17-portfolio-auto-publish-design.md`

## Global Constraints

- Repo: `C:/Users/sahii/sahiixx-agency`. Portfolio repo: `C:/Users/sahii/Projects/portfolio`.
- Python style: `from __future__ import annotations`, line length 120, pydantic v2 (`model_dump(mode="json")`).
- No new third-party dependencies. No GitHub-write or Cloudflare-API client.
- New specialized adapters: standalone `*_adapter`-style file + factory in `_SPECIALIZED_ADAPTERS` (engine.py) + ecosystem entry + routing rule in `config/agency.yaml` (repo AGENTS.md rules).
- Workflow templates use single-brace substitution: `{name}`, NOT `{{ name }}` (`workflows.py:354`).
- `RepoNode` has `is_fork` but NO `archived` field — do not reference one.
- Tests run from repo root: `.venv/Scripts/python -m pytest tests/ -q` (never pass `--basetemp`).
- `registry.json` shape: `{"updated_at": ..., "module_count": N, "modules": [<RepoNode dump>, ...]}`.
- Windows: run npm/git/wrangler through `shell=True` string commands so `.cmd` shims resolve.

---

### Task 1: Registry diff + `registry.module_added` bus event

**Files:**
- Modify: `sahiixx_agency/core/engine.py:933-938` (`AgencyEngine.sync_repos`)
- Test: `tests/test_core.py` (append; fixtures already exist there)

**Interfaces:**
- Consumes: `self.registry.modules` (property → `list[RepoNode]`), `self.bus.publish(BusMessage)` (async), `BusMessage(id, topic, sender, payload)` — `uuid` and `BusMessage` are already imported in engine.py.
- Produces: bus topic `registry.module_added`, payload = flat `RepoNode.model_dump(mode="json")` (top-level keys `id`, `name`, `description`, ...). Task 6's workflow template depends on `{name}` resolving from this flat payload. `engine._on_bus_message` (engine.py:516) already routes `registry.*` topics to event workflows.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_core.py`:

```python
@pytest.mark.asyncio
async def test_sync_repos_publishes_module_added_for_new_modules(engine):
    events: list = []
    engine.bus.subscribe("registry.module_added", events.append)

    # Baseline sync (registry empty -> full): establishes baseline, no events.
    await engine.sync_repos("sahiixx")
    assert events == []

    # Second sync introduces one new module -> exactly one event.
    new_mod = RepoNode(
        id="new-module",
        name="new-module",
        full_name="sahiixx/new-module",
        url="https://github.com/sahiixx/new-module",
        category=RepoCategory.AGENT_FRAMEWORK,
    )

    async def fake_discover_round_two(username):
        engine.registry._modules[new_mod.id] = new_mod
        return [*FAKE_MODULES, new_mod]

    engine.registry.discover = fake_discover_round_two
    discovered = await engine.sync_repos("sahiixx")

    assert len(discovered) == 3
    assert len(events) == 1
    assert events[0].topic == "registry.module_added"
    assert events[0].sender == "engine"
    assert events[0].payload["id"] == "new-module"
    assert events[0].payload["name"] == "new-module"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_core.py::test_sync_repos_publishes_module_added_for_new_modules -v`
Expected: FAIL — `assert len(events) == 1` (0 events published; no diff logic exists).

- [ ] **Step 3: Implement the diff + publish**

Replace `sync_repos` (engine.py:933-938) with:

```python
    async def sync_repos(self, username: str | None = None) -> list[RepoNode]:
        """Sync all GitHub repos into the registry."""
        user = username or self.config.github_username
        before = {m.id for m in self.registry.modules}
        discovered = await self.registry.discover(user)
        self.memory.log_event("registry.sync", {"username": user, "count": len(discovered)})
        if before:
            for module in discovered:
                if module.id not in before:
                    await self.bus.publish(
                        BusMessage(
                            id=f"msg_{uuid.uuid4().hex[:8]}",
                            topic="registry.module_added",
                            sender="engine",
                            payload=module.model_dump(mode="json"),
                        )
                    )
        return discovered
```

Baseline guard: an empty `before` set means first-ever sync — publish nothing.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_core.py -v`
Expected: all PASS, including pre-existing `test_sync_repos` (its fixture syncs into an empty registry → baseline → no events → behavior unchanged).

- [ ] **Step 5: Commit**

```bash
git add sahiixx_agency/core/engine.py tests/test_core.py
git commit -m "feat(engine): publish registry.module_added for newly discovered modules"
```

---

### Task 2: Config plumbing — AgencyConfig field, agency.yaml block, ecosystem entry, routing rule

**Files:**
- Modify: `sahiixx_agency/core/models.py` (AgencyConfig, after the `notifications` field, ~line 344)
- Modify: `config/agency.yaml` (three separate locations, below)
- Test: `tests/test_core.py` (append next to the other config tests)

**Interfaces:**
- Consumes: `AgencyConfig` (models.py:307) — plain pydantic model, dict fields are the established pattern (`ecosystem`, `notifications`).
- Produces: `AgencyConfig.portfolio_publisher: dict[str, Any]` (Task 5's factory reads it); ecosystem id `portfolio_publisher` (Task 5 registration key); routing rule targeting `portfolio_publisher` (must be FIRST in `routing_rules` — first-match-wins).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_core.py`:

```python
def test_agency_config_portfolio_publisher_defaults():
    assert AgencyConfig().portfolio_publisher == {}


def test_agency_config_portfolio_publisher_accepts_settings():
    config = AgencyConfig(portfolio_publisher={"enabled": True, "dry_run": False})
    assert config.portfolio_publisher["enabled"] is True


def test_agency_yaml_portfolio_publisher_wiring():
    import yaml

    with open("config/agency.yaml", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    assert data["portfolio_publisher"]["enabled"] is False
    assert data["portfolio_publisher"]["dry_run"] is True
    assert data["ecosystem"]["portfolio_publisher"]["category"] == "content_media"
    assert data["routing_rules"][0]["target"] == "portfolio_publisher"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_core.py -k portfolio_publisher -v`
Expected: FAIL — `TypeError: AgencyConfig() got an unexpected keyword argument` (pydantic forbids the unknown field) and `KeyError` in the YAML test.

- [ ] **Step 3: Add the AgencyConfig field**

In `sahiixx_agency/core/models.py`, immediately after the `notifications` field block in `AgencyConfig`:

```python
    # Portfolio auto-publish settings loaded from agency.yaml
    portfolio_publisher: dict[str, Any] = Field(
        default_factory=dict,
        description="Portfolio publisher settings: enabled, dry_run, repo_path, ignore",
    )
```

- [ ] **Step 4: Edit config/agency.yaml — ecosystem entry**

Immediately after the `web_intel:` ecosystem entry (the one with `bus_channel: "intel.*"`):

```yaml
  portfolio_publisher:
    repo: sahiixx-agency
    url: https://github.com/sahiixx/sahiixx-agency
    role: "Draft and publish portfolio entries for newly shipped modules"
    capabilities: [portfolio-publish, content-generation, pages-deploy]
    category: content_media
    bus_channel: "publish.*"
    protocol: internal
    priority: 1
```

- [ ] **Step 5: Edit config/agency.yaml — routing rule**

At the TOP of the `routing_rules:` list (before the existing first rule, whose target is `web_intel`):

```yaml
  - pattern: 'publish portfolio|portfolio entry|add .* to (the )?portfolio'
    target: portfolio_publisher
```

- [ ] **Step 6: Edit config/agency.yaml — settings block**

Next to the top-level `notifications:` block (top-level key, same indentation):

```yaml
portfolio_publisher:
  enabled: false
  dry_run: true
  repo_path: "C:/Users/sahii/Projects/portfolio"
  ignore: []
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_core.py -k portfolio_publisher -v`
Expected: 3 PASS.

- [ ] **Step 8: Commit**

```bash
git add sahiixx_agency/core/models.py config/agency.yaml tests/test_core.py
git commit -m "feat(config): portfolio_publisher settings, ecosystem entry, routing rule"
```

---

### Task 3: Entry drafting module — ProjectEntry, prompt, TS renderer

**Files:**
- Create: `sahiixx_agency/adapters/portfolio_entry.py`
- Test: `tests/adapters/test_portfolio_entry.py`

**Interfaces:**
- Consumes: nothing from other tasks (pure module; pydantic v2).
- Produces (Task 4 imports these exact names): `ACCENTS: list[str]`, `ProjectEntry` (pydantic model), `slugify(name: str) -> str`, `next_index(existing: list[str]) -> str`, `build_prompt(module: dict, readme: str, *, index: str, accent: str, year: str) -> str`, `entry_from_response(raw: str, *, module: dict, index: str, accent: str, year: str) -> ProjectEntry`, `render_ts_entry(entry: ProjectEntry) -> str`.

- [ ] **Step 1: Write the failing tests**

Create `tests/adapters/test_portfolio_entry.py`:

```python
"""Tests for portfolio entry drafting and rendering."""

from __future__ import annotations

import json

import pytest

from sahiixx_agency.adapters.portfolio_entry import (
    ProjectEntry,
    entry_from_response,
    next_index,
    render_ts_entry,
    slugify,
)

MODULE = {
    "id": "postiz-app",
    "name": "postiz-app",
    "description": "Social media scheduling tool",
    "language": "TypeScript",
    "url": "https://github.com/sahiixx/postiz-app",
}

ENTRY_JSON = json.dumps({
    "name": "Postiz",
    "tagline": "Schedule everything, everywhere.",
    "description": "A social scheduling pipeline with queue workers and channel adapters.",
    "longDescription": ["Paragraph one.", "Paragraph two."],
    "problem": "Posting to five networks by hand does not scale.",
    "architecture": "Next.js · workers · Redis queues",
    "statusNote": "Running locally.",
    "highlights": ["Multi-channel", "Queue-based", "Self-hosted"],
    "role": "Architect & sole engineer",
    "status": "Shipped",
    "stack": ["TypeScript", "Next.js", "Redis"],
    "url": "https://github.com/sahiixx/postiz-app",
})


def test_slugify():
    assert slugify("postiz-app") == "postiz-app"
    assert slugify("SAHIIX OS") == "sahiix-os"
    assert slugify("deer_flow 2.0") == "deer-flow-2-0"


def test_next_index():
    assert next_index(["01", "02", "04"]) == "05"
    assert next_index([]) == "01"


def test_entry_from_response_fills_caller_fields():
    entry = entry_from_response(ENTRY_JSON, module=MODULE, index="05", accent="#34d399", year="2026")
    assert entry.id == "postiz-app"
    assert entry.index == "05"
    assert entry.accent == "#34d399"
    assert entry.year == "2026"
    assert entry.name == "Postiz"


def test_entry_from_response_strips_prose_around_json():
    raw = "Here is your entry:\n```json\n" + ENTRY_JSON + "\n```\nDone."
    entry = entry_from_response(raw, module=MODULE, index="05", accent="#34d399", year="2026")
    assert entry.id == "postiz-app"


def test_entry_from_response_rejects_missing_fields():
    with pytest.raises(Exception):
        entry_from_response('{"name": "X"}', module=MODULE, index="05", accent="#34d399", year="2026")


def test_render_ts_entry_matches_data_ts_style():
    entry = entry_from_response(ENTRY_JSON, module=MODULE, index="05", accent="#34d399", year="2026")
    rendered = render_ts_entry(entry)
    assert rendered.startswith("  {\n")
    assert rendered.endswith("  },")
    assert '    id: "postiz-app",' in rendered
    assert '    index: "05",' in rendered
    assert '    accent: "#34d399",' in rendered
    assert "    longDescription: [\n" in rendered
    # no optional fields rendered
    assert "featured" not in rendered
    assert "image" not in rendered
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/adapters/test_portfolio_entry.py -v`
Expected: FAIL — `ModuleNotFoundError: sahiixx_agency.adapters.portfolio_entry`.

- [ ] **Step 3: Implement the module**

Create `sahiixx_agency/adapters/portfolio_entry.py`:

```python
"""Portfolio entry drafting: prompt building, validation, and TypeScript rendering."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field

ACCENTS = ["#f59e0b", "#ff4d4d", "#7c5cff", "#22d3ee", "#34d399", "#f472b6"]


class ProjectEntry(BaseModel):
    """A portfolio `Project` entry (mirrors src/data.ts, minus optional fields)."""

    id: str
    index: str
    name: str
    tagline: str
    description: str
    longDescription: list[str] = Field(min_length=1, max_length=4)
    problem: str
    architecture: str
    statusNote: str
    highlights: list[str] = Field(min_length=2, max_length=6)
    role: str = "Architect & sole engineer"
    status: str = "Shipped"
    stack: list[str] = Field(min_length=1, max_length=10)
    year: str
    url: str
    accent: str


def slugify(name: str) -> str:
    """Kebab-case slug for a module name."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "module"


def next_index(existing: list[str]) -> str:
    """Next zero-padded index after the max existing one (e.g. ["01", "04"] -> "05")."""
    numbers = [int(i) for i in existing if i.isdigit()]
    return f"{max(numbers) + 1 if numbers else 1:02d}"


def build_prompt(module: dict[str, Any], readme: str, *, index: str, accent: str, year: str) -> str:
    """Prompt that makes the LLM return strict JSON for a portfolio entry."""
    meta = {
        "name": module.get("name"),
        "description": module.get("description"),
        "language": module.get("language"),
        "topics": module.get("topics"),
        "stars": module.get("stars"),
        "url": module.get("url"),
    }
    return (
        "You are writing a new entry for Sahil's curated developer portfolio "
        "(sahiix-portfolio.pages.dev). Voice: confident, concrete, engineer-to-engineer; "
        "short sentences; no buzzwords, no emoji, no exclamation marks.\n\n"
        "Module metadata (JSON):\n" + json.dumps(meta, indent=2) + "\n\n"
        "README excerpt:\n" + (readme[:3000] or "(no README available)") + "\n\n"
        "Return ONLY a JSON object with exactly these keys:\n"
        '- "name": display name (short, may restyle e.g. "sahiixx-agency" -> "SAHIIX Agency")\n'
        '- "tagline": one line, <= 80 chars\n'
        '- "description": 2-3 sentences, <= 300 chars\n'
        '- "longDescription": 2 paragraphs, each 1-3 sentences\n'
        '- "problem": the pain it solves, 1-2 sentences\n'
        '- "architecture": key components joined with " · ", one line\n'
        '- "statusNote": where it runs / maturity, one line\n'
        '- "highlights": 3-4 concrete bullets\n'
        '- "role": "Architect & sole engineer"\n'
        '- "status": "Shipped"\n'
        '- "stack": 3-7 technologies\n'
        '- "url": best public URL (live site if obvious, else the repo URL)\n'
        "Do not include id, index, year, or accent — they are set by the caller "
        f"(index {index}, year {year}, accent {accent}). No markdown fences."
    )


def _extract_json(raw: str) -> str:
    """Pull the first {...} block out of an LLM response (handles prose and fences)."""
    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not match:
        raise ValueError("LLM response contained no JSON object")
    return match.group(0)


def entry_from_response(raw: str, *, module: dict[str, Any], index: str, accent: str, year: str) -> ProjectEntry:
    """Parse + validate the LLM JSON response into a ProjectEntry."""
    data = json.loads(_extract_json(raw))
    data.setdefault("id", slugify(str(module.get("name") or module.get("id") or "module")))
    data["index"] = index
    data["accent"] = accent
    data["year"] = year
    data.setdefault("url", module.get("url") or "")
    if not data.get("name"):
        data["name"] = str(module.get("name") or data["id"])
    return ProjectEntry.model_validate(data)


def _ts_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _ts_string_array(values: list[str], indent: int) -> str:
    pad = " " * indent
    if len(values) <= 4 and all(len(v) < 40 for v in values):
        return "[" + ", ".join(_ts_string(v) for v in values) + "]"
    inner = ",\n".join(f"{pad}  {_ts_string(v)}" for v in values)
    return "[\n" + inner + ",\n" + pad + "]"


def render_ts_entry(entry: ProjectEntry) -> str:
    """Render the entry as a TS object literal matching src/data.ts style (2-space indent)."""
    lines = ["  {"]
    lines.append(f"    id: {_ts_string(entry.id)},")
    lines.append(f"    index: {_ts_string(entry.index)},")
    lines.append(f"    name: {_ts_string(entry.name)},")
    lines.append(f"    tagline: {_ts_string(entry.tagline)},")
    lines.append(f"    description: {_ts_string(entry.description)},")
    lines.append(f"    longDescription: {_ts_string_array(entry.longDescription, 4)},")
    lines.append(f"    problem: {_ts_string(entry.problem)},")
    lines.append(f"    architecture: {_ts_string(entry.architecture)},")
    lines.append(f"    statusNote: {_ts_string(entry.statusNote)},")
    lines.append(f"    highlights: {_ts_string_array(entry.highlights, 4)},")
    lines.append(f"    role: {_ts_string(entry.role)},")
    lines.append(f"    status: {_ts_string(entry.status)},")
    lines.append(f"    stack: {_ts_string_array(entry.stack, 4)},")
    lines.append(f"    year: {_ts_string(entry.year)},")
    lines.append(f"    url: {_ts_string(entry.url)},")
    lines.append(f"    accent: {_ts_string(entry.accent)},")
    lines.append("  },")
    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/adapters/test_portfolio_entry.py -v`
Expected: 6 PASS.

- [ ] **Step 5: Commit**

```bash
git add sahiixx_agency/adapters/portfolio_entry.py tests/adapters/test_portfolio_entry.py
git commit -m "feat(portfolio): entry drafting module with TS renderer"
```

---

### Task 4: PortfolioPublisherAdapter — gates, registry lookup, insertion, pipeline

**Files:**
- Create: `sahiixx_agency/adapters/portfolio_publisher.py`
- Test: `tests/adapters/test_portfolio_publisher.py`

**Interfaces:**
- Consumes: Task 3 (`ProjectEntry`, `build_prompt`, `entry_from_response`, `next_index`, `render_ts_entry`, `slugify`, `ACCENTS`); `BaseAdapter` (`adapters/base.py` — constructor kwargs `clone_base_dir`, `network_policy`, `audit_logger`); `LLMMessage`/`NotificationChannel` from `core.models`; `llm_manager.chat(messages=[...], temperature=..., max_tokens=...)` → object with `.content: str`; `notifications.send(NotificationChannel, title, body)` (async).
- Produces (Task 5 instantiates this exact signature): `PortfolioPublisherAdapter(*, settings: dict, llm_manager: Any | None, notifications: Any | None, **base_kwargs)`; `execute(payload: dict) -> dict` returning `{"status": "success"|"failed"|"skipped", ...}` (same convention as `WebIntelAdapter`).
- Marker contract (Task 7 depends on it): `MARKER = "// __OPA_PORTFOLIO_INSERT__"`; insertion replaces the marker with `rendered + "\n  " + MARKER`, so new entries land directly above the marker line, inside the `projects` array.

- [ ] **Step 1: Write the failing tests**

Create `tests/adapters/test_portfolio_publisher.py`:

```python
"""Tests for the portfolio publisher adapter."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from sahiixx_agency.adapters.portfolio_publisher import MARKER, PortfolioPublisherAdapter

DATA_TS = """export interface Project { id: string }
export const projects: Project[] = [
  {
    id: "opa",
    index: "04",
  },
  // __OPA_PORTFOLIO_INSERT__
];
"""

MODULE = {
    "id": "postiz-app",
    "name": "postiz-app",
    "description": "Social media scheduling tool",
    "language": "TypeScript",
    "url": "https://github.com/sahiixx/postiz-app",
    "is_fork": False,
}

ENTRY_JSON = json.dumps({
    "name": "Postiz",
    "tagline": "Schedule everything, everywhere.",
    "description": "A social scheduling pipeline.",
    "longDescription": ["One.", "Two."],
    "problem": "Posting by hand does not scale.",
    "architecture": "Next.js · workers · Redis",
    "statusNote": "Running locally.",
    "highlights": ["Multi-channel", "Queue-based"],
    "role": "Architect & sole engineer",
    "status": "Shipped",
    "stack": ["TypeScript", "Next.js", "Redis"],
    "url": "https://github.com/sahiixx/postiz-app",
})


class FakeLLM:
    def __init__(self, content: str = ENTRY_JSON) -> None:
        self.content = content

    async def chat(self, messages, **kwargs):
        return SimpleNamespace(content=self.content)


class FakeNotifications:
    def __init__(self) -> None:
        self.sent: list[tuple] = []

    async def send(self, channel, title, body, **kwargs):
        self.sent.append((channel, title, body))


@pytest.fixture
def workspace(tmp_path):
    """Temp portfolio repo + registry, returns (repo_dir, settings)."""
    repo = tmp_path / "portfolio"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "data.ts").write_text(DATA_TS, encoding="utf-8")
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({"modules": [MODULE]}), encoding="utf-8")
    settings = {
        "enabled": True,
        "dry_run": True,
        "repo_path": str(repo),
        "registry_path": str(registry),
        "ignore": [],
        "notify_channels": ["sse"],
    }
    return repo, settings


def make_adapter(settings, **overrides):
    return PortfolioPublisherAdapter(
        settings=settings,
        llm_manager=overrides.get("llm", FakeLLM()),
        notifications=overrides.get("notifications", FakeNotifications()),
        clone_base_dir=overrides.get("clone_base_dir", "/tmp"),
    )


@pytest.mark.asyncio
async def test_disabled_returns_skipped(workspace):
    repo, settings = workspace
    settings["enabled"] = False
    result = await make_adapter(settings).execute({"brief": "publish portfolio entry for postiz-app"})
    assert result["status"] == "skipped"
    assert "disabled" in result["reason"]


@pytest.mark.asyncio
async def test_no_module_match_fails_and_notifies(workspace):
    repo, settings = workspace
    notifications = FakeNotifications()
    adapter = make_adapter(settings, notifications=notifications)
    result = await adapter.execute({"brief": "publish portfolio entry for nonexistent"})
    assert result["status"] == "failed"
    assert len(notifications.sent) == 1


@pytest.mark.asyncio
async def test_gate_skips_fork(workspace):
    repo, settings = workspace
    registry = settings["registry_path"]
    forked = dict(MODULE, is_fork=True)
    with open(registry, "w", encoding="utf-8") as fh:
        json.dump({"modules": [forked]}, fh)
    result = await make_adapter(settings).execute({"brief": "publish portfolio entry for postiz-app"})
    assert result == {"status": "skipped", "reason": "fork", "module": "postiz-app"}


@pytest.mark.asyncio
async def test_gate_skips_already_published(workspace):
    repo, settings = workspace
    data_ts = repo / "src" / "data.ts"
    data_ts.write_text(DATA_TS.replace('id: "opa"', 'id: "postiz-app"'), encoding="utf-8")
    result = await make_adapter(settings).execute({"brief": "publish portfolio entry for postiz-app"})
    assert result["status"] == "skipped"
    assert result["reason"] == "already published"


@pytest.mark.asyncio
async def test_missing_marker_fails(workspace):
    repo, settings = workspace
    (repo / "src" / "data.ts").write_text(DATA_TS.replace(MARKER, "// nothing"), encoding="utf-8")
    result = await make_adapter(settings).execute({"brief": "publish portfolio entry for postiz-app"})
    assert result["status"] == "failed"
    assert "marker" in result["error"].lower()


@pytest.mark.asyncio
async def test_dry_run_renders_without_touching_disk(workspace):
    repo, settings = workspace
    notifications = FakeNotifications()
    adapter = make_adapter(settings, notifications=notifications)
    data_ts = repo / "src" / "data.ts"
    before = data_ts.read_text(encoding="utf-8")
    result = await adapter.execute({"brief": "publish portfolio entry for postiz-app"})
    assert result["status"] == "success"
    assert result["dry_run"] is True
    assert 'id: "postiz-app"' in result["entry"]
    assert data_ts.read_text(encoding="utf-8") == before
    assert any("dry-run" in title.lower() for _, title, _ in notifications.sent)


@pytest.mark.asyncio
async def test_full_pipeline_inserts_builds_commits_deploys(workspace, monkeypatch):
    repo, settings = workspace
    settings["dry_run"] = False
    adapter = make_adapter(settings)
    calls: list[str] = []

    async def fake_run(command, *, cwd, timeout):
        calls.append(command)
        if command.startswith("git status"):
            return True, ""  # clean tree
        return True, "ok"

    monkeypatch.setattr(adapter, "_run", fake_run)
    result = await adapter.execute({"brief": "publish portfolio entry for postiz-app"})
    assert result["status"] == "success"
    assert result["deployed"] is True
    content = (repo / "src" / "data.ts").read_text(encoding="utf-8")
    assert 'id: "postiz-app"' in content
    assert content.index('id: "postiz-app"') < content.index(MARKER)
    assert any("npm run build" in c for c in calls)
    assert any("wrangler pages deploy dist" in c for c in calls)
    assert any("git commit" in c for c in calls)
    assert any(c == "git push" for c in calls)


@pytest.mark.asyncio
async def test_build_failure_restores_data_ts(workspace, monkeypatch):
    repo, settings = workspace
    settings["dry_run"] = False
    adapter = make_adapter(settings)
    data_ts = repo / "src" / "data.ts"
    original = data_ts.read_text(encoding="utf-8")

    async def fake_run(command, *, cwd, timeout):
        if command.startswith("git status"):
            return True, ""
        if command == "npm run build":
            return False, "TS error: boom"
        return True, "ok"

    monkeypatch.setattr(adapter, "_run", fake_run)
    result = await adapter.execute({"brief": "publish portfolio entry for postiz-app"})
    assert result["status"] == "failed"
    assert "build failed" in result["error"]
    assert data_ts.read_text(encoding="utf-8") == original


@pytest.mark.asyncio
async def test_dirty_repo_aborts_before_drafting(workspace, monkeypatch):
    repo, settings = workspace
    settings["dry_run"] = False
    llm = FakeLLM()
    adapter = make_adapter(settings, llm=llm)
    llm_called = []

    original_chat = llm.chat

    async def tracking_chat(messages, **kwargs):
        llm_called.append(True)
        return await original_chat(messages, **kwargs)

    llm.chat = tracking_chat

    async def fake_run(command, *, cwd, timeout):
        if command.startswith("git status"):
            return True, " M src/data.ts"
        return True, "ok"

    monkeypatch.setattr(adapter, "_run", fake_run)
    result = await adapter.execute({"brief": "publish portfolio entry for postiz-app"})
    assert result["status"] == "failed"
    assert "uncommitted" in result["error"]
    assert llm_called == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/adapters/test_portfolio_publisher.py -v`
Expected: FAIL — `ModuleNotFoundError: sahiixx_agency.adapters.portfolio_publisher`.

- [ ] **Step 3: Implement the adapter**

Create `sahiixx_agency/adapters/portfolio_publisher.py`:

```python
"""Publish portfolio entries for newly shipped modules."""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from typing import Any

from sahiixx_agency.adapters.base import BaseAdapter
from sahiixx_agency.adapters.portfolio_entry import (
    ACCENTS,
    ProjectEntry,
    build_prompt,
    entry_from_response,
    next_index,
    render_ts_entry,
    slugify,
)
from sahiixx_agency.core.models import LLMMessage, NotificationChannel

MARKER = "// __OPA_PORTFOLIO_INSERT__"


class PortfolioPublisherAdapter(BaseAdapter):
    """Draft, insert, build, commit, deploy, and notify one portfolio entry."""

    def __init__(
        self,
        *,
        settings: dict[str, Any] | None = None,
        llm_manager: Any | None = None,
        notifications: Any | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.clone_base_dir = kwargs.get("clone_base_dir", "./data/repos")
        self.settings = settings or {}
        self.llm = llm_manager
        self.notifications = notifications

    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.get("enabled", False):
            return {"status": "skipped", "reason": "portfolio_publisher disabled"}

        intent = str(payload.get("brief") or payload.get("module") or "")
        module = self._find_module(intent)
        if module is None:
            return await self._fail(f"No registry module matched intent: {intent!r}")
        slug = slugify(str(module.get("name") or module.get("id")))

        skip = self._gates(module, slug)
        if skip:
            return {"status": "skipped", "reason": skip, "module": slug}

        repo = self.settings.get("repo_path", "")
        data_ts = os.path.join(repo, "src", "data.ts")
        original = self._read_file(data_ts)
        if original is None:
            return await self._fail(f"data.ts not readable at {data_ts}")
        if MARKER not in original:
            return await self._fail(f"Insertion marker missing in {data_ts}")
        if not await self._git_clean(repo):
            return await self._fail("portfolio repo has uncommitted changes in src/data.ts")

        existing = self._existing_indices(original)
        index = next_index(existing)
        accent = ACCENTS[len(existing) % len(ACCENTS)]
        year = str(datetime.now(timezone.utc).year)
        readme = self._read_readme(module)
        prompt = build_prompt(module, readme, index=index, accent=accent, year=year)
        try:
            entry = await self._draft(prompt, module=module, index=index, accent=accent, year=year)
        except Exception as exc:  # noqa: BLE001
            return await self._fail(f"LLM drafting failed: {exc}")

        rendered = render_ts_entry(entry)
        if self.settings.get("dry_run", True):
            await self._notify("Portfolio dry-run", f"Rendered entry for {entry.name}:\n\n{rendered}")
            return {"status": "success", "dry_run": True, "module": slug, "entry": rendered}

        self._write_file(data_ts, original.replace(MARKER, rendered + "\n  " + MARKER))

        ok, out = await self._run("npm run build", cwd=repo, timeout=300)
        if not ok:
            self._write_file(data_ts, original)
            return await self._fail(f"portfolio build failed, data.ts restored:\n{out[-800:]}")

        ok, out = await self._run("git add src/data.ts", cwd=repo, timeout=60)
        if ok:
            ok, out = await self._run(f'git commit -m "feat: add {slug} to selected work [opa]"', cwd=repo, timeout=60)
        if not ok:
            self._write_file(data_ts, original)
            return await self._fail(f"git commit failed, data.ts restored:\n{out[-800:]}")

        ok, out = await self._run("npx wrangler pages deploy dist", cwd=repo, timeout=600)
        if not ok:
            return await self._fail(f"wrangler deploy failed (entry committed locally):\n{out[-800:]}")

        ok, _ = await self._run("git push", cwd=repo, timeout=120)
        push_note = "" if ok else "\n(git push failed — deploy is live, local commit not pushed)"
        await self._notify(
            "Portfolio updated",
            f"Published {entry.name} ({slug}) to sahiix-portfolio.pages.dev{push_note}",
        )
        return {"status": "success", "module": slug, "index": index, "deployed": True, "pushed": ok}

    # --- lookup + gates ---------------------------------------------------

    def _find_module(self, intent: str) -> dict[str, Any] | None:
        """Best registry match for a free-text intent (longest id/name contained in it)."""
        registry_path = self.settings.get("registry_path", "./data/registry.json")
        try:
            with open(registry_path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return None
        lowered = intent.lower()
        best: dict[str, Any] | None = None
        best_len = 0
        for module in data.get("modules", []):
            if not isinstance(module, dict):
                continue
            for key in (module.get("id"), module.get("name")):
                if key and key.lower() in lowered and len(key) > best_len:
                    best = module
                    best_len = len(key)
        return best

    def _gates(self, module: dict[str, Any], slug: str) -> str | None:
        if module.get("is_fork"):
            return "fork"
        if not (module.get("description") or "").strip():
            return "no description"
        if slug in set(self.settings.get("ignore") or []):
            return "ignored"
        data_ts = os.path.join(self.settings.get("repo_path", ""), "src", "data.ts")
        try:
            with open(data_ts, encoding="utf-8") as fh:
                if f'id: "{slug}"' in fh.read():
                    return "already published"
        except OSError:
            return "data.ts not readable"
        return None

    # --- drafting ---------------------------------------------------------

    async def _draft(
        self,
        prompt: str,
        *,
        module: dict[str, Any],
        index: str,
        accent: str,
        year: str,
    ) -> ProjectEntry:
        if self.llm is None:
            raise RuntimeError("LLM manager not configured")
        response = await self.llm.chat(
            messages=[
                LLMMessage(role="system", content="You output only valid JSON."),
                LLMMessage(role="user", content=prompt),
            ],
            temperature=0.4,
            max_tokens=1500,
        )
        return entry_from_response(response.content, module=module, index=index, accent=accent, year=year)

    def _read_readme(self, module: dict[str, Any]) -> str:
        clone_dir = os.path.join(self.clone_base_dir, str(module.get("name") or ""))
        for candidate in ("README.md", "readme.md", "README.MD"):
            readme = self._read_file(os.path.join(clone_dir, candidate))
            if readme:
                return readme
        return ""

    # --- file + process helpers -------------------------------------------

    @staticmethod
    def _existing_indices(source: str) -> list[str]:
        return re.findall(r'^\s{4}index: "(\d+)"', source, flags=re.MULTILINE)

    @staticmethod
    def _read_file(path: str) -> str | None:
        try:
            with open(path, encoding="utf-8") as fh:
                return fh.read()
        except OSError:
            return None

    @staticmethod
    def _write_file(path: str, content: str) -> None:
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)

    async def _git_clean(self, repo: str) -> bool:
        ok, out = await self._run("git status --porcelain -- src/data.ts", cwd=repo, timeout=30)
        return ok and not out.strip()

    async def _run(self, command: str, *, cwd: str, timeout: int) -> tuple[bool, str]:
        def _call() -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                command,
                cwd=cwd,
                shell=True,
                timeout=timeout,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

        try:
            proc = await asyncio.to_thread(_call)
        except (subprocess.TimeoutExpired, OSError) as exc:
            return False, str(exc)
        output = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode == 0, output

    # --- notifications ------------------------------------------------------

    async def _notify(self, title: str, body: str) -> None:
        if self.notifications is None:
            return
        for channel in self.settings.get("notify_channels") or ["sse"]:
            try:
                await self.notifications.send(NotificationChannel(channel), title, body)
            except Exception:  # noqa: BLE001
                continue

    async def _fail(self, reason: str) -> dict[str, Any]:
        await self._notify("Portfolio publish failed", reason)
        return {"status": "failed", "error": reason}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/adapters/test_portfolio_publisher.py -v`
Expected: 8 PASS.

- [ ] **Step 5: Commit**

```bash
git add sahiixx_agency/adapters/portfolio_publisher.py tests/adapters/test_portfolio_publisher.py
git commit -m "feat(portfolio): publisher adapter with gates, rollback, deploy pipeline"
```

---

### Task 5: Factory + registration in the engine

**Files:**
- Modify: `sahiixx_agency/core/engine.py` — add `_make_portfolio_publisher` next to `_make_web_intel` (~line 346-356), register in `_SPECIALIZED_ADAPTERS` (~line 378-409)
- Test: `tests/test_core.py` (append)

**Interfaces:**
- Consumes: Task 4's `PortfolioPublisherAdapter(*, settings, llm_manager, notifications, **kwargs)`; `AgencyConfig.portfolio_publisher` (Task 2); `LLMManager(config.llm, AgencyMemory(config.data_dir, backend=config.memory_backend))` (engine.py:468 pattern); `NotificationManager(config=config.notifications)` (engine.py:465 pattern); `os` is already imported in engine.py.
- Produces: factory `_make_portfolio_publisher(config, network_policy, audit_logger, task)`; registration keys `portfolio_publisher` and `portfolio-publisher` (Task 6's routing target).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_core.py`:

```python
def test_portfolio_publisher_factory_registered():
    from sahiixx_agency.core.engine import _SPECIALIZED_ADAPTERS

    assert "portfolio_publisher" in _SPECIALIZED_ADAPTERS
    assert "portfolio-publisher" in _SPECIALIZED_ADAPTERS


def test_portfolio_publisher_factory_builds_adapter(tmp_path):
    from sahiixx_agency.core.engine import _make_portfolio_publisher

    config = AgencyConfig(data_dir=str(tmp_path))
    task = AgencyTask(id="t1", intent="publish portfolio entry for postiz-app", payload={})
    adapter, payload = _make_portfolio_publisher(config, None, None, task)
    assert adapter.settings["registry_path"].endswith("registry.json")
    assert adapter.settings["notify_channels"] == ["sse"]
    assert payload["brief"] == "publish portfolio entry for postiz-app"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_core.py -k portfolio_publisher_factory -v`
Expected: FAIL — `ImportError: cannot import name '_make_portfolio_publisher'`.

- [ ] **Step 3: Implement the factory**

In `sahiixx_agency/core/engine.py`, immediately after `_make_web_intel`:

```python
def _make_portfolio_publisher(config, network_policy, audit_logger, task):
    from sahiixx_agency.adapters.portfolio_publisher import PortfolioPublisherAdapter
    from sahiixx_agency.core.llm import LLMManager
    from sahiixx_agency.core.memory import AgencyMemory
    from sahiixx_agency.core.notifications import NotificationManager

    settings = dict(config.portfolio_publisher)
    settings.setdefault("registry_path", os.path.join(config.data_dir, "registry.json"))
    if not settings.get("notify_channels"):
        telegram_cfg = (config.notifications or {}).get("telegram") or {}
        has_token = bool(telegram_cfg.get("bot_token") or os.environ.get("TELEGRAM_BOT_TOKEN"))
        settings["notify_channels"] = ["telegram", "sse"] if has_token else ["sse"]
    adapter = PortfolioPublisherAdapter(
        settings=settings,
        llm_manager=LLMManager(config.llm, AgencyMemory(config.data_dir, backend=config.memory_backend)),
        notifications=NotificationManager(config=config.notifications),
        clone_base_dir=os.path.join(config.data_dir, "repos"),
        network_policy=network_policy,
        audit_logger=audit_logger,
    )
    payload = dict(task.payload)
    payload.setdefault("brief", task.intent)
    return adapter, payload
```

- [ ] **Step 4: Register in `_SPECIALIZED_ADAPTERS`**

Add two entries to the dict (keep alphabetical-ish neighborhood, next to `"postiz"`):

```python
    "portfolio_publisher": _make_portfolio_publisher,
    "portfolio-publisher": _make_portfolio_publisher,
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_core.py -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add sahiixx_agency/core/engine.py tests/test_core.py
git commit -m "feat(engine): register portfolio_publisher specialized adapter"
```

---

### Task 6: Event workflow definition

**Files:**
- Create: `data/workflows/portfolio-publisher.json`
- Test: `tests/test_workflows.py` (append)

**Interfaces:**
- Consumes: Task 1's flat payload (so `{name}` resolves via `_render_template`); Task 5's routing (`publish portfolio entry for ...` → `portfolio_publisher`). `WorkflowDefinition` model fields match `data/workflows/site-monitor.json` exactly.
- Produces: enabled event workflow on topic `registry.module_added`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_workflows.py`:

```python
def test_portfolio_publisher_workflow_definition():
    import json

    with open("data/workflows/portfolio-publisher.json", encoding="utf-8") as fh:
        definition = WorkflowDefinition.model_validate(json.load(fh))
    assert definition.id == "portfolio-publisher"
    assert definition.trigger == "event"
    assert definition.event_topic == "registry.module_added"
    assert definition.enabled is True
    assert len(definition.steps) == 1
    step = definition.steps[0]
    assert step.action == "dispatch"
    assert step.requires_approval is False
    assert "{name}" in (step.intent_template or "")
```

Check the imports at the top of `tests/test_workflows.py`; if `WorkflowDefinition` is not already imported there, add `from sahiixx_agency.core.models import WorkflowDefinition` inside the test (as shown) or at top matching existing style.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_workflows.py::test_portfolio_publisher_workflow_definition -v`
Expected: FAIL — `FileNotFoundError: data/workflows/portfolio-publisher.json`.

- [ ] **Step 3: Create the workflow JSON**

Create `data/workflows/portfolio-publisher.json` (shape mirrors `site-monitor.json`; replace the two timestamps with the current UTC time):

```json
{
  "id": "portfolio-publisher",
  "name": "Portfolio Auto-Publisher",
  "description": "Publishes a portfolio entry when a new module appears in the registry",
  "trigger": "event",
  "schedule": null,
  "event_topic": "registry.module_added",
  "steps": [
    {
      "id": "publish_entry",
      "name": "Publish portfolio entry",
      "action": "dispatch",
      "target": "portfolio_publisher",
      "intent_template": "publish portfolio entry for {name}",
      "payload": {},
      "requires_approval": false,
      "next_on_success": null,
      "next_on_failure": null,
      "condition": null
    }
  ],
  "enabled": true,
  "created_at": "2026-07-17T00:00:00Z",
  "updated_at": "2026-07-17T00:00:00Z"
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_workflows.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add data/workflows/portfolio-publisher.json tests/test_workflows.py
git commit -m "feat(workflows): portfolio-publisher event workflow"
```

---

### Task 7: Portfolio repo insertion marker

**Files:**
- Modify: `C:/Users/sahii/Projects/portfolio/src/data.ts` (line ~223-224, end of the `projects` array)

**Interfaces:**
- Consumes: Task 4's `MARKER` contract (`// __OPA_PORTFOLIO_INSERT__`, inserted entries land above it).
- Produces: a live insertion point in the real portfolio repo.

- [ ] **Step 1: Insert the marker**

In `C:/Users/sahii/Projects/portfolio/src/data.ts`, the `projects` array currently ends:

```ts
    accent: "#22d3ee",
  },
];
```

Change it to:

```ts
    accent: "#22d3ee",
  },
  // __OPA_PORTFOLIO_INSERT__
];
```

- [ ] **Step 2: Verify the portfolio still builds**

Run: `cd C:/Users/sahii/Projects/portfolio && npm run build`
Expected: build succeeds (comment-only change), `dist/` regenerated.

- [ ] **Step 3: Commit in the portfolio repo**

```bash
cd C:/Users/sahii/Projects/portfolio
git add src/data.ts
git commit -m "chore: add OPA portfolio insertion marker"
```

Do NOT touch `.gitignore` or the untracked `CLAUDE.md` already in that repo's working tree — stage `src/data.ts` only.

---

### Task 8: End-to-end verification — dry-run, enable, live smoke

**Files:**
- Modify: `config/agency.yaml` (flip `portfolio_publisher.enabled` / `dry_run`)

**Interfaces:**
- Consumes: everything above. Uses `opa dispatch` (CLI) which routes via the new rule and executes through the worker.

- [ ] **Step 1: Full test suite green**

Run: `cd C:/Users/sahii/sahiixx-agency && .venv/Scripts/python -m pytest tests/ -q`
Expected: `483+ passed` (previous 483 + all new tests).

- [ ] **Step 2: Pick a candidate module**

Run:

```bash
cd C:/Users/sahii/sahiixx-agency && .venv/Scripts/python -c "import json; mods=json.load(open('data/registry.json', encoding='utf-8'))['modules']; data=open(r'C:/Users/sahii/Projects/portfolio/src/data.ts', encoding='utf-8').read(); print('\n'.join(m['id'] for m in mods if (m.get('description') or '').strip() and not m.get('is_fork') and f'id: \"{m[\"id\"]}\"' not in data))"
```

Expected: a list of publishable module ids. Pick one well-known repo (e.g. `deer-flow`, `loop-engineering`, `background-agents` — whichever appears and has a real README).

- [ ] **Step 3: Dry-run against the real portfolio**

Set in `config/agency.yaml`: `portfolio_publisher.enabled: true` (leave `dry_run: true`).

Run: `cd C:/Users/sahii/sahiixx-agency && .venv/Scripts/opa.exe dispatch "publish portfolio entry for <chosen-id>"`

Expected: task completes; result `status: success`, `dry_run: true`, rendered `entry` in the task result (visible via `opa task status <id>` or the API); notification sent (Telegram if `TELEGRAM_BOT_TOKEN` is set, else SSE/console). Verify `git -C C:/Users/sahii/Projects/portfolio status --porcelain -- src/data.ts` is EMPTY (dry-run touched nothing).

- [ ] **Step 4: Eyeball the rendered entry**

Read the rendered entry in the task result / notification. Check: voice matches the existing four entries (concrete, no hype), stack list sane, URL correct, no truncated sentences. If the LLM output is weak, tune the prompt in `sahiixx_agency/adapters/portfolio_entry.py` (`build_prompt`) and repeat Step 3. Do not proceed until the entry reads like the hand-written ones.

- [ ] **Step 5: Go live for one module**

Set in `config/agency.yaml`: `portfolio_publisher.dry_run: false`.

Run: `.venv/Scripts/opa.exe dispatch "publish portfolio entry for <chosen-id>"`

Expected: entry inserted above the marker in `src/data.ts`; `npm run build` passes; commit `feat: add <slug> to selected work [opa]` appears in the portfolio repo log; `wrangler pages deploy dist` succeeds; `git push` succeeds; success notification arrives. Verify the live site shows the new card: fetch `https://sahiix-portfolio.pages.dev/` and check the module name appears (allow ~30s for Pages propagation).

If any step fails, the adapter must have rolled back / notified per the error matrix — investigate before retrying.

- [ ] **Step 6: Commit the config flip**

```bash
cd C:/Users/sahii/sahiixx-agency
git add config/agency.yaml
git commit -m "chore(config): enable portfolio auto-publish"
```

From this point, every `opa sync` that discovers a genuinely new repo fires the full pipeline automatically.

---

## Execution notes

- Tasks 1-6 are independent of the real portfolio repo and can run back-to-back; Task 7 touches the live portfolio repo; Task 8 is manual verification by the orchestrator (not a subagent task — it makes live deploy decisions).
- After Task 8 Step 6, update `docs/superpowers/specs/2026-07-17-portfolio-auto-publish-design.md` status line to "implemented".
