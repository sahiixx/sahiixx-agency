# AGENTS.md — sahiixx-agency (OPA)

Quick reference for agents working in this repo. For full architecture, see `CLAUDE.md`.

## Setup

```bash
pip install -e ".[dev]"          # install package + dev deps (creates `opa` CLI)
cd dashboard && npm install      # dashboard deps (separate Vite project)
```

## Key Commands

| What | Command |
|------|---------|
| Run all tests | `pytest tests/ -q` |
| Run one test | `pytest tests/test_core.py::test_name -v` |
| Lint + format | `ruff check . && ruff format .` |
| Typecheck | `mypy sahiixx_agency` |
| Start API server | `opa serve` (port 8082) |
| Start MCP server | `python -m sahiixx_agency.mcp_server.main` (stdio) or `MCP_TRANSPORT=sse` for HTTP |
| Start dashboard | `cd dashboard && npm run dev` (port 3000) |
| Sync GitHub repos | `opa sync` (needs `GITHUB_TOKEN` env) |
| Dispatch a task | `opa dispatch "intent here"` |

**On Windows:** Use `.venv\Scripts\python -m pytest` directly. The `Makefile` uses bash paths (`.venv/bin/*`) and won't work in PowerShell.

## Gotchas an Agent Would Miss

- **pytest basetemp:** `conftest.py` at repo root creates a unique temp dir per session via `tempfile.mkdtemp`. Never pass `--basetemp=./.pytest_tmp` — that dir gets locked on Windows and causes 200+ cascading errors. Just run `pytest tests/`.

- **Docker vs local ports:** Docker runs on 8080 (uvicorn directly). Local dev is 8082 (`config.api_port`). These are deliberately different.

- **Auth gate is opt-in:** With `OPA_API_KEY` unset, all API endpoints are open. Set it before any non-localhost exposure. Webhook paths (`/webhooks/*`, `/telegram/webhook`) are always exempt from the key gate.

- **Telegram `allowed_chat_ids: []`** means allow ALL chats — prints a startup warning. Set it before exposing the bot token.

- **`Makefile` is WSL-only:** Uses `.venv/bin/*` bash paths. On Windows, run commands directly.

- **Adapter registration:** New specialized adapters go in `_SPECIALIZED_ADAPTERS` dict in `engine.py`. Don't extend the `if/elif` chain. Category adapters use `adapters/<category>/runner.py` (subclass `BaseAdapter`); specialized adapters are standalone `*_adapter.py` files.

- **Ecosystem stubs:** `config/agency.yaml` has ~23 YAML-only module entries that materialize lightweight `RepoNode` objects. These work before `opa sync` runs and provide routing metadata.

- **Gitignored runtime files:** `data/registry.json`, `data/repos/`, `runtime-pids.json`, `*.log`, `.env` — don't expect them in a fresh clone. `data_test/` holds test fixtures.

- **API auto-sync on startup:** If the registry is empty on server start, `lifespan` in `api/main.py` automatically runs `sync_repos()`. Don't assume `opa sync` must be called manually.

- **Dashboard is a separate project:** `dashboard/` is Vite + React 19 + TS, not part of the Python package. Vite proxies `/api` to `:8082` and `/dashboard/graph-data` to `:8082`. The `@` alias maps to `dashboard/src/`.

- **Dockerfile runs as non-root:** Creates an `opa` user. The Docker image ships pre-built `dashboard/dist/` (no `npm build` in the image).

- **MCP server transport:** Default is stdio. Set `MCP_TRANSPORT=sse` for HTTP mode (binds `MCP_HOST:MCP_PORT`, default `127.0.0.1:8081`). The MCP server (`mcp_server/main.py`) is distinct from the MCP adapter (`adapters/mcp/runner.py`) which clones/runs *external* MCP repos.

- **Routing is regex-first, then keyword scoring.** `routing_rules` in `agency.yaml` are compiled regex patterns matched against intent (first-match-wins, order matters). Fallback is bag-of-words scoring across all registered modules. No LLM in the hot path.

## CI

- GitHub Actions: pytest on Python 3.12 + 3.13 (`ci.yml`)
- Docker publish to GHCR on push to main/master + version tags (`docker-publish.yml`)
- Pre-commit: gitleaks (secrets) + ruff (lint/format)

## Code Style

- Python 3.11+ syntax (`from __future__ import annotations`)
- Line length 120 (ruff), target py310
- mypy strict=false but `warn_return_any` + `warn_unused_ignores` enabled
- Tests excluded from mypy
- Pydantic v2 models with `model_dump(mode="json")` for serialization

## Adding an Adapter

1. Create `sahiixx_agency/adapters/<category>/runner.py` (subclass `BaseAdapter`) for category adapters, or a standalone `*_adapter.py` for specialized adapters
2. Add ecosystem entry in `config/agency.yaml`
3. Add routing rule in `config/agency.yaml`
4. Register factory in `_SPECIALIZED_ADAPTERS` dict in `engine.py` (if specialized)
