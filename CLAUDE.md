# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

One Person Agency (OPA) — a Python framework that auto-discovers GitHub repos, registers them as modules, routes natural-language intents to the best module, and exposes everything through a Typer CLI (`opa`), a FastAPI server, an MCP server, and a separate React/D3 dashboard. Package is `sahiixx_agency`; entry point `opa` → `sahiixx_agency.cli.main:app`.

## Commands

```bash
# Backend (Python)
pip install -e .                              # install (creates `opa` + `sahiixx-agency` console scripts)
opa sync                                      # discover GitHub repos into data/registry.json (needs GITHUB_TOKEN)
opa serve                                     # FastAPI on config.api_port (8082); --reload for dev
opa dispatch "<intent>"                       # route + run an intent through the engine
opa task-status <id>                          # NOTE: command is `task-status`, not `task status`
python -m sahiixx_agency.mcp_server.main      # MCP server (stdio; sse if MCP_TRANSPORT=sse)

# Tests — IMPORTANT on Windows
.venv\Scripts\python -m pytest tests/ -q      # use the venv python; do NOT pass --basetemp=./.pytest_tmp
.venv\Scripts\python -m pytest tests/test_core.py::test_dispatch_task -v   # single test

# Lint / typecheck (dev deps)
ruff check .          ; ruff format .
mypy sahiixx_agency    # tests/ is excluded in [tool.mypy]

# Dashboard (separate npm project in dashboard/)
cd dashboard && npm install
cd dashboard && npm run dev      # Vite on :3000
cd dashboard && npm run build    # tsc -b && vite build → dashboard/dist
cd dashboard && npm run lint     # eslint .
cd dashboard && npm run test     # vitest run
```

`Makefile` and `scripts/*.sh` use `.venv/bin/*` bash paths — **WSL/bash only, not PowerShell**. On Windows run the commands above directly.

## Architecture (big picture)

The core is `sahiixx_agency/core/engine.py` — `AgencyEngine` wires together every subsystem and owns the task lifecycle. A task flows: `cli/api/mcp dispatch` → `engine.dispatch()` → `InputSanitizer` → `TaskRouter.route()` → risk gate → `_execute_task()` → adapter → result.

**Routing (`core/router.py`)** is **regex rules + keyword scoring** — no embeddings, no LLM in the hot path. `TaskRouter` first matches the intent against `routing_rules` in `config/agency.yaml` (compiled regex, first-match-wins), resolving the rule's `target` to an ecosystem module; if no rule hits, it falls back to `_score_modules` (bag-of-words + stars + category bonus). Rules that shadow earlier ones are unreachable — order matters.

**Ecosystem stubs vs real adapters.** `config/agency.yaml` has an `ecosystem:` block of ~21 YAML-only module entries (repo/url/role/protocol). These are *not* Python — they materialize a lightweight `RepoNode` so routing metadata propagates even before `opa sync` runs. Real adapters live in `sahiixx_agency/adapters/` (thin `BaseAdapter` subclasses per category + standalone specialized adapters).

**Adapter dispatch (`engine.py` `_execute_task`)** is driven by a module-level registry, `_SPECIALIZED_ADAPTERS` (dict of normalized `module_id` → factory). **Add a new specialized adapter by registering a factory in that dict — do not extend the `if/elif` chain.** Unknown module ids fall through to `GenericAdapter`; no module but a category → `_run_category_adapter` picks the most-starred module in the category and sets `task.module_id`.

**Config is `config/agency.yaml`** (`OPA_CONFIG` env points elsewhere). Top-level: `api_port`/`dashboard_port`/`mcp_port`, `github_token`, `discovery`, `approval` (auto-approve low-risk), `security` (sanitize/audit/network lists), `telegram`, `llm` (4 pluggable providers, all keys null), `ecosystem`, `routing_rules`. Secret fields ship as `null`; real values come from env vars.

**Subsystems in `core/`:** `registry` (GitHub discovery + classification into `RepoCategory`), `runner` (clone + subprocess exec), `bus` (pub/sub), `memory` + `ltm` (events + long-term), `approval` (risk-gated task approval — `approve_by_task`/`reject_by_task` are the public API; don't touch `_by_task`), `costs`, `llm`, `workflows` + `scheduler`, `notifications`, `marketplace`, `metrics` (health checks + Prometheus), `security` (`InputSanitizer`, `NetworkPolicy`, `SecretsManager`), `dependency_scanner`, `chat`, `logger`.

**API (`api/main.py`)**: uvicorn-served FastAPI. Two middlewares: `api_key_gate` (mutating methods require `X-OPA-API-Key` header **only when `OPA_API_KEY` env is set** — disabled in local dev) and `api_prefix_middleware` (lets the dashboard call `/api/*`). CORS is explicit origins via `OPA_CORS_ORIGINS` (defaults to local dashboard dev servers); webhooks (`/webhooks/*`, `/telegram/webhook`) are exempt from the key gate.

**MCP server (`mcp_server/main.py`)**: FastMCP, 10 tools (`list_modules`, `dispatch_task`, `run_intel_scout`, `agency_stats`, `sync_registry`, `list_workflows`, `run_workflow`, `send_notification`, `get_metrics`, `get_health`). stdio by default; SSE binds `MCP_HOST:MCP_PORT` (8081) if `MCP_TRANSPORT=sse`. Distinct from `adapters/mcp/runner.py` (`McpAdapter`), which clones/runs *external* MCP repos.

**Discovery (`sahiixx_agency/discovery/`)**: a separate package (not under `core/`). `pipeline.py` orchestrates repo discovery; `intent_signals.py` classifies free text into intent tiers — `SignalTier` (HOT/WARM/NURTURE) via `HOT_SIGNAL_PATTERNS`/`WARM_SIGNAL_PATTERNS`/`NURTURE_SIGNAL_PATTERNS` plus a `GCC_SIGNAL_PATTERNS` set — `detect_signals()` matches patterns, `_get_outreach_angle()` derives a hook, `aggregate_signals()` rolls up per entity. This is the in-engine counterpart to the lead-scoring logic in the `.claude/skills/outbound-prospecting` skill — keep the two aligned if you evolve signal definitions.

**Dashboard (`dashboard/`)** is a top-level Vite + React 19 + TS + D3 SPA — **not** part of the Python package. Graph data comes from `GET /dashboard/graph-data` (FastAPI, iterates the registry) with a bundled static fallback `dashboard/public/graph_data.json` so it renders without the backend.

**Project skills (`.claude/skills/`)**: two Claude Code skills with stdlib-only runnable scripts — `realestate-deal-analyzer` (Dubai/GCC investment metrics + investor brief; run `analyze_deal.py --json '{...}'`) and `outbound-prospecting` (lead scoring via saturating curve + outreach drafting; run `score_leads.py < leads.json`). On Windows, pass JSON via `--json` with backslash-escaped quotes, or `cmd /c "python script.py < file.json"` — PowerShell's native-command piping strips double-quotes and re-encodes stdin. `docs/skills/gcc-outbound-skill-builder.md` is a separate *prompt* for generating more skills with Fable/Opus.

## Deploy

`docker-compose.yml` is the only target that runs both services (agency-api :8080 + agency-mcp :8081, healthchecks, restart policy). Docker uses port 8080 internally (nginx proxies `agency-api:8080`); **local dev uses 8082** (`config.api_port`) — the two are deliberately different. `Dockerfile` runs as root, single-stage, and ships the pre-built `dashboard/dist/` (no `npm build` in the image). CI (`.github/workflows/`) runs pytest on py3.12/3.13 and publishes to GHCR.

## Gotchas

- **Windows pytest basetemp lock.** `conftest.py` at the repo root forces a fresh `tempfile.mkdtemp` per session to dodge a Windows `PermissionError` on the default pytest temp dir. **Never run pytest with `--basetemp=./.pytest_tmp`** — that dir can get a locked ACL and cascade 200+ setup errors. Plain `pytest tests/` is correct; the conftest handles basetemp.
- **`data/repos/`, `data/registry.json`, `runtime-pids.json`, `*.log`, `.env` are gitignored** — don't expect them in a fresh clone. `data/registry.json` is the live registry (written by `opa sync`); `data_test/` holds test fixtures.
- **Adding an adapter**: create `adapters/<category>/` with a `runner.py` (subclass `BaseAdapter`) or a standalone `*_adapter.py` exposing `async run(node, payload)`, add an `ecosystem:` entry in `agency.yaml`, add a `routing_rules` entry, and register a factory in `_SPECIALIZED_ADAPTERS` (engine.py) if it's a specialized adapter.
- **Auth gate is opt-in.** With `OPA_API_KEY` unset, every API endpoint is open (local dev). Set `OPA_API_KEY` before any non-localhost exposure; then mutating methods require `X-OPA-API-Key`.
- **Telegram `allowed_chat_ids: []` means allow all chats** — the bot prints a startup warning. Set it (config or `TELEGRAM_ALLOWED_CHAT_IDS` env) before exposing the token.