# Register Five Additional External Repos Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Register `relaymux`, `claude-obsidian`, `youtube-automation-agent`, `letta-code`, and `career-ops` as config-only OPA ecosystem modules with categories, registry keywords, and routing rules.

**Architecture:** Add three new `RepoCategory` values, extend registry classification rules, append ecosystem entries and routing rules to `agency.yaml`, and add focused tests for categories, classification, and routing.

**Tech Stack:** Python 3.12, Pydantic v2, PyYAML, pytest, pytest-asyncio.

## Global Constraints

- Target Python 3.10+ syntax; use `from __future__ import annotations` in all new files.
- Line length 120 (ruff default in project).
- Type-hint everything.
- No live network calls in tests.
- Follow existing patterns in the codebase.
- All changes stay scoped to config, models, registry keywords, and tests.

## File Structure

| File | Responsibility |
|------|----------------|
| `sahiixx_agency/core/models.py` | Add `CONTENT_MEDIA`, `KNOWLEDGE`, `CAREER` to `RepoCategory`. |
| `sahiixx_agency/core/registry.py` | Add new category keyword rules and extend existing rules. |
| `config/agency.yaml` | Add 5 ecosystem entries and 5 routing rules. |
| `tests/test_core.py` | Add tests for new categories, classification, and routing. |

---

### Task 1: Add new `RepoCategory` values

**Files:**
- Modify: `sahiixx_agency/core/models.py:33-45`
- Test: `tests/test_core.py`

**Interfaces:**
- Consumes: existing `RepoCategory` enum.
- Produces: `RepoCategory.CONTENT_MEDIA`, `RepoCategory.KNOWLEDGE`, `RepoCategory.CAREER`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_core.py`:

```python
from sahiixx_agency.core.models import RepoCategory


def test_new_repo_categories_exist():
    assert RepoCategory.CONTENT_MEDIA.value == "content_media"
    assert RepoCategory.KNOWLEDGE.value == "knowledge"
    assert RepoCategory.CAREER.value == "career"
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
cd /c/Users/sahii/sahiixx-agency/.worktrees/feature/t3mp3st-hiring-agent
source .venv/Scripts/activate
pytest tests/test_core.py::test_new_repo_categories_exist -v
```

Expected: `FAIL` with `AttributeError` for the missing enum values.

- [ ] **Step 3: Add the category values**

Modify `sahiixx_agency/core/models.py` inside `RepoCategory`, after `INFRASTRUCTURE` and before `FORK`:

```python
    CONTENT_MEDIA = "content_media"        # YouTube / media automation
    KNOWLEDGE = "knowledge"                # Obsidian / second brain
    CAREER = "career"                      # Job search / career agents
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```bash
pytest tests/test_core.py::test_new_repo_categories_exist -v
```

Expected: `PASS`.

- [ ] **Step 5: Commit**

```bash
git add sahiixx_agency/core/models.py tests/test_core.py
git commit -m "feat(models): add CONTENT_MEDIA, KNOWLEDGE, CAREER repo categories"
```

---

### Task 2: Extend registry classification keywords

**Files:**
- Modify: `sahiixx_agency/core/registry.py:14-125`
- Test: `tests/test_core.py`

**Interfaces:**
- Consumes: new `RepoCategory` values from Task 1.
- Produces: updated `CATEGORY_RULES` list with new rules and keywords.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_core.py`:

```python
import pytest

from sahiixx_agency.core.registry import _classify_repo


def test_classify_repo_content_media():
    category = _classify_repo(
        "youtube-automation-agent",
        "Automated YouTube channel management",
        ["youtube", "content"],
    )
    assert category == RepoCategory.CONTENT_MEDIA


def test_classify_repo_knowledge():
    category = _classify_repo(
        "claude-obsidian",
        "Obsidian vault second brain",
        ["obsidian", "knowledge"],
    )
    assert category == RepoCategory.KNOWLEDGE


def test_classify_repo_career():
    category = _classify_repo(
        "career-ops",
        "AI-powered job search system",
        ["career", "resume"],
    )
    assert category == RepoCategory.CAREER


def test_classify_repo_agent_framework_relaymux_letta():
    category = _classify_repo(
        "relaymux",
        "Telegram remote control for tmux coding agents",
        ["agent", "telegram", "tmux"],
    )
    assert category == RepoCategory.AGENT_FRAMEWORK

    category = _classify_repo(
        "letta-code",
        "Stateful agents with persistent memory",
        ["letta", "memory", "stateful"],
    )
    assert category == RepoCategory.AGENT_FRAMEWORK
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
pytest tests/test_core.py::test_classify_repo_content_media tests/test_core.py::test_classify_repo_knowledge tests/test_core.py::test_classify_repo_career tests/test_core.py::test_classify_repo_agent_framework_relaymux_letta -v
```

Expected: `FAIL` with `AssertionError` because repos classify as `UNCATEGORIZED`.

- [ ] **Step 3: Update `CATEGORY_RULES`**

Modify `sahiixx_agency/core/registry.py`:

1. Extend the `AGENT_FRAMEWORK` keyword list to include:

```python
            "relaymux",
            "letta",
            "stateful",
            "memory",
            "remote",
            "tmux",
```

2. Append three new category rules before the final `]`:

```python
    (
        RepoCategory.CONTENT_MEDIA,
        [
            "youtube",
            "video",
            "content",
            "media",
            "channel",
        ],
    ),
    (
        RepoCategory.KNOWLEDGE,
        [
            "obsidian",
            "vault",
            "wiki",
            "second brain",
            "knowledge",
            "notes",
        ],
    ),
    (
        RepoCategory.CAREER,
        [
            "career",
            "job",
            "resume",
            "cv",
            "hiring",
            "linkedin",
            "apply",
        ],
    ),
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
pytest tests/test_core.py::test_classify_repo_content_media tests/test_core.py::test_classify_repo_knowledge tests/test_core.py::test_classify_repo_career tests/test_core.py::test_classify_repo_agent_framework_relaymux_letta -v
```

Expected: all `PASS`.

- [ ] **Step 5: Run lint and full suite**

Run:

```bash
ruff check sahiixx_agency tests
pytest tests/ -v
```

Expected: ruff clean; all tests pass.

- [ ] **Step 6: Commit**

```bash
git add sahiixx_agency/core/registry.py tests/test_core.py
git commit -m "feat(registry): classify content, knowledge, and career repos"
```

---

### Task 3: Add ecosystem entries and routing rules to `agency.yaml`

**Files:**
- Modify: `config/agency.yaml`
- Test: manual YAML validation

**Interfaces:**
- Consumes: existing ecosystem and routing rule schema.
- Produces: 5 new ecosystem entries and 5 new routing rules.

- [ ] **Step 1: Add ecosystem entries**

Insert after the `hiring_agent` entry in `config/agency.yaml`:

```yaml
  # ── Agent Runtimes ──
  relaymux:
    repo: relaymux
    owner: mupt-ai
    url: https://github.com/mupt-ai/relaymux
    role: "Telegram remote control for tmux-based coding agents"
    bus_channel: "agent.*"
    protocol: subprocess
    priority: 2
    tags: [agent, telegram, tmux, remote, relaymux]

  letta_code:
    repo: letta-code
    owner: letta-ai
    url: https://github.com/letta-ai/letta-code
    role: "Stateful local agents with persistent memory"
    bus_channel: "agent.*"
    protocol: subprocess
    priority: 2
    tags: [agent, memory, stateful, letta, local]

  # ── Knowledge / Second Brain ──
  claude_obsidian:
    repo: claude-obsidian
    owner: AgriciDaniel
    url: https://github.com/AgriciDaniel/claude-obsidian
    role: "Obsidian vault + Claude Code second-brain workflow"
    bus_channel: "knowledge.*"
    protocol: subprocess
    priority: 2
    tags: [obsidian, knowledge, vault, wiki, claude]

  # ── Content / Media ──
  youtube_agent:
    repo: youtube-automation-agent
    owner: darkzOGx
    url: https://github.com/darkzOGx/youtube-automation-agent
    role: "Automated YouTube channel management"
    bus_channel: "content.*"
    protocol: subprocess
    priority: 2
    tags: [youtube, content, media, video, channel]

  # ── Career / Hiring ──
  career_ops:
    repo: career-ops
    owner: santifer
    url: https://github.com/santifer/career-ops
    role: "AI job-search command center built on Claude Code"
    bus_channel: "career.*"
    protocol: subprocess
    priority: 2
    tags: [career, job, resume, cv, hiring]
```

- [ ] **Step 2: Add routing rules**

Append to `routing_rules`:

```yaml
  - pattern: "relaymux|telegram|tmux|remote.agent"
    target: relaymux
  - pattern: "obsidian|second.brain|vault|wiki|notes"
    target: claude_obsidian
  - pattern: "youtube|video|channel|content|media"
    target: youtube_agent
  - pattern: "letta|persistent.memory|stateful.agent|local.agent"
    target: letta_code
  - pattern: "job|career|apply|linkedin|cv|resume"
    target: career_ops
```

- [ ] **Step 3: Validate YAML syntax**

Run:

```bash
python -c "import yaml; yaml.safe_load(open('config/agency.yaml'))" && echo "YAML OK"
```

Expected: prints `YAML OK`.

- [ ] **Step 4: Commit**

```bash
git add config/agency.yaml
git commit -m "feat(config): register relaymux, obsidian, youtube, letta, career-ops"
```

---

### Task 4: Add routing tests for the new modules

**Files:**
- Modify: `tests/test_core.py`

**Interfaces:**
- Consumes: existing `TaskRouter`, `AgencyConfig`, `RepoNode`, `MessageBus`, `RepoRegistry`.
- Produces: tests proving red-team intents route to the new modules.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_core.py`:

```python
@pytest.fixture
def router_with_five_new_modules(tmp_path):
    config = AgencyConfig(
        data_dir=str(tmp_path),
        routing_rules=[
            {"pattern": "relaymux|telegram|tmux|remote.agent", "target": "relaymux"},
            {"pattern": "obsidian|second.brain|vault|wiki|notes", "target": "claude_obsidian"},
            {"pattern": "youtube|video|channel|content|media", "target": "youtube_agent"},
            {"pattern": "letta|persistent.memory|stateful.agent|local.agent", "target": "letta_code"},
            {"pattern": "job|career|apply|linkedin|cv|resume", "target": "career_ops"},
        ],
        ecosystem={
            "relaymux": {
                "repo": "relaymux",
                "owner": "mupt-ai",
                "url": "https://github.com/mupt-ai/relaymux",
                "role": "Telegram remote control",
            },
            "claude_obsidian": {
                "repo": "claude-obsidian",
                "owner": "AgriciDaniel",
                "url": "https://github.com/AgriciDaniel/claude-obsidian",
                "role": "Obsidian second brain",
            },
            "youtube_agent": {
                "repo": "youtube-automation-agent",
                "owner": "darkzOGx",
                "url": "https://github.com/darkzOGx/youtube-automation-agent",
                "role": "YouTube automation",
            },
            "letta_code": {
                "repo": "letta-code",
                "owner": "letta-ai",
                "url": "https://github.com/letta-ai/letta-code",
                "role": "Stateful local agents",
            },
            "career_ops": {
                "repo": "career-ops",
                "owner": "santifer",
                "url": "https://github.com/santifer/career-ops",
                "role": "AI job search",
            },
        },
    )
    registry = RepoRegistry(data_dir=str(tmp_path))
    for key in ("relaymux", "claude_obsidian", "youtube_agent", "letta_code", "career_ops"):
        registry._modules[key] = RepoNode(
            id=key,
            name=key.replace("_", "-"),
            full_name=f"owner/{key.replace('_', '-')}",
            url=f"https://github.com/owner/{key.replace('_', '-')}",
        )
    return TaskRouter(registry, MessageBus(), config=config)


@pytest.mark.asyncio
async def test_router_resolves_relaymux_intent(router_with_five_new_modules):
    task = await router_with_five_new_modules.route("launch a remote agent via telegram")
    assert task.module_id == "relaymux"


@pytest.mark.asyncio
async def test_router_resolves_obsidian_intent(router_with_five_new_modules):
    task = await router_with_five_new_modules.route("open my obsidian second brain vault")
    assert task.module_id == "claude_obsidian"


@pytest.mark.asyncio
async def test_router_resolves_youtube_intent(router_with_five_new_modules):
    task = await router_with_five_new_modules.route("automate my youtube channel")
    assert task.module_id == "youtube_agent"


@pytest.mark.asyncio
async def test_router_resolves_letta_intent(router_with_five_new_modules):
    task = await router_with_five_new_modules.route("run a stateful letta agent with memory")
    assert task.module_id == "letta_code"


@pytest.mark.asyncio
async def test_router_resolves_career_intent(router_with_five_new_modules):
    task = await router_with_five_new_modules.route("apply to jobs on linkedin")
    assert task.module_id == "career_ops"
```

- [ ] **Step 2: Run the tests to verify they pass**

Run:

```bash
pytest tests/test_core.py::test_router_resolves_relaymux_intent tests/test_core.py::test_router_resolves_obsidian_intent tests/test_core.py::test_router_resolves_youtube_intent tests/test_core.py::test_router_resolves_letta_intent tests/test_core.py::test_router_resolves_career_intent -v
```

Expected: all `PASS`.

- [ ] **Step 3: Run full suite and lint**

Run:

```bash
ruff check sahiixx_agency tests
pytest tests/ -v
```

Expected: ruff clean; all tests pass.

- [ ] **Step 4: Commit**

```bash
git add tests/test_core.py
git commit -m "test(routing): cover five new external repo routing rules"
```

---

## Self-Review

**1. Spec coverage:**
- New `RepoCategory` values — Task 1.
- Registry classification keywords — Task 2.
- `agency.yaml` ecosystem entries — Task 3.
- `agency.yaml` routing rules — Task 3.
- Tests for categories, classification, routing — Tasks 1, 2, 4.

**2. Placeholder scan:**
- No "TBD", "TODO", or vague steps.
- All code blocks contain concrete code.
- All commands include expected output.

**3. Type consistency:**
- `RepoCategory` enum values are strings.
- `_classify_repo` signature unchanged.
- `TaskRouter` config schema unchanged.

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-07-05-register-five-external-repos.md`.**

Two execution options:

1. **Subagent-Driven (recommended)** — Dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — Execute tasks in this session using `executing-plans`, batch execution with checkpoints.

Auto-mode is active. I will proceed with **Subagent-Driven** execution.
