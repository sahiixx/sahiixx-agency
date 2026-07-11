# AGENTS.md — sahiixx-agency (OPA)

Quick reference for agents working in this repo. For full architecture, see `CLAUDE.md`.

## Setup

```bash
pip install -e ".[dev]"          # install package + dev deps (creates `opa` CLI)
cd dashboard && npm install      # dashboard deps
```

## Key Commands

| What | Command |
|------|---------|
| Run all tests | `pytest tests/ -q` |
| Run one test | `pytest tests/test_core.py::test_name -v` |
| Lint + format | `ruff check . && ruff format .` |
| Typecheck | `mypy sahiixx_agency` |
| Start API server | `opa serve` (port 8082) |
| Start MCP server | `python -m sahiixx_agency.mcp_server.main` |
| Start dashboard | `cd dashboard && npm run dev` (port 3000) |
| Sync GitHub repos | `opa sync` (needs `GITHUB_TOKEN` env) |
| Dispatch a task | `opa dispatch "intent here"` |

**On Windows:** Use `.venv\Scripts\python -m pytest` directly. The `Makefile` uses bash paths (`.venv/bin/*`) and won't work in PowerShell.

## Gotchas an Agent Would Miss

- **pytest basetemp:** `conftest.py` at repo root creates a unique temp dir per session via `tempfile.mkdtemp`. Never pass `--basetemp=./.pytest_tmp` — that dir gets locked on Windows and causes 200+ cascading errors. Just run `pytest tests/`.

- **Docker vs local ports:** Docker internal port is 8080 (nginx proxy). Local dev is 8082 (`config.api_port`). These are deliberately different.

- **Auth gate is opt-in:** With `OPA_API_KEY` unset, all API endpoints are open. Set it before any non-localhost exposure.

- **Telegram `allowed_chat_ids: []`** means allow ALL chats — prints a startup warning. Set it before exposing the bot token.

- **`Makefile` is WSL-only:** Uses `.venv/bin/*` bash paths. On Windows, run commands directly.

- **Adapter registration:** New specialized adapters go in `_SPECIALIZED_ADAPTERS` dict in `engine.py`. Don't extend the `if/elif` chain.

- **Ecosystem stubs:** `config/agency.yaml` has ~21 YAML-only module entries that materialize lightweight `RepoNode` objects. These work before `opa sync` runs.

- **Gitignored runtime files:** `data/registry.json`, `data/repos/`, `runtime-pids.json`, `*.log`, `.env` — don't expect them in a fresh clone. `data_test/` holds test fixtures.

## CI

- GitHub Actions: pytest on Python 3.12 + 3.13 (`ci.yml`)
- Docker publish to GHCR on push to main/master (`docker-publish.yml`)
- Pre-commit: gitleaks (secrets) + ruff (lint/format)

## Code Style

- Python 3.10+ syntax (`from __future__ import annotations`)
- Line length 120 (ruff), target py310
- mypy strict=false but `warn_return_any` + `warn_unused_ignores` enabled
- Tests excluded from mypy
- Pydantic v2 models with `model_dump(mode="json")` for serialization

## Adding an Adapter

1. Create `sahiixx_agency/adapters/<category>/runner.py` (subclass `BaseAdapter`)
2. Add ecosystem entry in `config/agency.yaml`
3. Add routing rule in `config/agency.yaml`
4. Register factory in `_SPECIALIZED_ADAPTERS` dict in `engine.py` (if specialized)
