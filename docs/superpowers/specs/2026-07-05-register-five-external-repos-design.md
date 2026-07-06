# Design: Register Five Additional External Repos in OPA

**Date:** 2026-07-05  
**Status:** Approved for implementation  
**Author:** Kimi Code CLI

## 1. Scope & Goals

Register five external repositories as config-only OPA ecosystem modules, using the existing generic `RepoRunner` / `BaseAdapter` execution path (no custom adapters in this pass):

- **[`mupt-ai/relaymux`](https://github.com/mupt-ai/relaymux)** — Telegram remote control + tmux coding-agent launcher.
- **[`AgriciDaniel/claude-obsidian`](https://github.com/AgriciDaniel/claude-obsidian)** — Obsidian vault + Claude Code second-brain workflow.
- **[`darkzOGx/youtube-automation-agent`](https://github.com/darkzOGx/youtube-automation-agent)** — Automated YouTube channel management (research, scripting, publishing, analytics).
- **[`letta-ai/letta-code`](https://github.com/letta-ai/letta-code)** — Stateful local agents with persistent memory.
- **[`santifer/career-ops`](https://github.com/santifer/career-ops)** — AI job-search command center built on Claude Code.

Goals:

1. Add three new `RepoCategory` values to `sahiixx_agency/core/models.py`.
2. Add five ecosystem entries to `config/agency.yaml`.
3. Add routing rules so natural-language intents resolve to the correct module.
4. Update registry classification keywords so auto-sync can categorize these repos if they are ever fetched via GitHub API.
5. Add/update tests for categories and routing.
6. Keep changes minimal and config-only; defer custom adapters.

## 2. Category Model

Add to `sahiixx_agency/core/models.py` in `RepoCategory`:

```python
class RepoCategory(str, Enum):
    """Canonical categories for repos."""

    AGENT_FRAMEWORK = "agent_framework"
    VOICE_AI = "voice_ai"
    REAL_ESTATE = "real_estate"
    SECURITY = "security"
    MCP_TOOL = "mcp_tool"
    COOKBOOK = "cookbook"
    OS_PLATFORM = "os_platform"
    INFRASTRUCTURE = "infrastructure"
    CONTENT_MEDIA = "content_media"        # YouTube / media automation
    KNOWLEDGE = "knowledge"                # Obsidian / second brain
    CAREER = "career"                      # Job search / career agents
    FORK = "fork"
    UNCATEGORIZED = "uncategorized"
```

Mapping of repos to categories:

| Repo | Category |
|------|----------|
| `mupt-ai/relaymux` | `AGENT_FRAMEWORK` |
| `AgriciDaniel/claude-obsidian` | `KNOWLEDGE` |
| `darkzOGx/youtube-automation-agent` | `CONTENT_MEDIA` |
| `letta-ai/letta-code` | `AGENT_FRAMEWORK` |
| `santifer/career-ops` | `CAREER` |

## 3. Registry Classification Keywords

Update `sahiixx_agency/core/registry.py` `CATEGORY_RULES` so auto-sync can classify these domains:

- Add to `AGENT_FRAMEWORK`: `relaymux`, `letta`, `stateful`, `memory`, `remote`, `tmux`.
- Add to `SECURITY` (existing): `redteam`, `exploit` (already partially covered).
- Add to `MCP_TOOL` (existing): `harness` (already partially covered).
- Add new `CONTENT_MEDIA` rule with keywords: `youtube`, `video`, `content`, `media`, `channel`.
- Add new `KNOWLEDGE` rule with keywords: `obsidian`, `vault`, `wiki`, `second brain`, `knowledge`, `notes`.
- Add new `CAREER` rule with keywords: `career`, `job`, `resume`, `cv`, `hiring`, `linkedin`, `apply`.

## 4. Configuration Changes

### 4.1 New ecosystem entries in `config/agency.yaml`

Insert under appropriate section comments:

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

### 4.2 New routing rules

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

## 5. Testing Strategy

| Test | File | What it verifies |
|------|------|------------------|
| New categories exist | `tests/test_core.py` | `RepoCategory.CONTENT_MEDIA`, `KNOWLEDGE`, `CAREER` are valid enum values. |
| Routing rules resolve | `tests/test_core.py` | Intents route to `relaymux`, `claude_obsidian`, `youtube_agent`, `letta_code`, `career_ops`. |
| Registry classification | `tests/test_core.py` | Keywords classify repos into new categories correctly. |
| YAML config valid | n/a (manual) | `python -c "import yaml; yaml.safe_load(open('config/agency.yaml'))"` passes. |
| No regressions | `pytest tests/ -v` | All existing tests still pass. |

## 6. Implementation Order

1. Add new `RepoCategory` values.
2. Update `CATEGORY_RULES` in `registry.py`.
3. Add ecosystem entries and routing rules to `config/agency.yaml`.
4. Add tests for categories, classification, and routing.
5. Run full test suite, lint, and type checks.
6. Commit.

## 7. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| External repos may change entrypoints. | Generic `RepoInspector` will surface `not_runnable`; custom adapters can be added later. |
| `relaymux` requires Telegram token + tmux. | Registration is routing/discovery only; actual runtime needs manual setup. |
| Routing-rule overlap with existing rules. | New rules are appended after existing rules. Specific terms (e.g., `relaymux`, `obsidian`, `letta`) still win; generic terms like `video` or `career` may overlap and are intentional. |
| New categories may not be recognized by dashboard. | Categories are additive; dashboard can be updated separately if needed. |
| Some module names contain mixed casing (`claude_obsidian`, `youtube_agent`, `letta_code`, `career_ops`). | Ecosystem keys use snake_case; repo names use actual GitHub repo names; `TaskRouter` already handles case-insensitive module-id matching via the previous `target_key` fallback. |

## 8. Open Questions

- Should any of these modules take routing precedence over existing modules? (Currently they are appended after existing rules.)
- Should a custom adapter be built for any of these in a follow-up? (`career_ops` and `youtube_agent` are the most likely candidates because they require config files.)
