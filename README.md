# One Person Agency (OPA) 🤖

**Unified AI orchestration for all 170+ repos.**

One Person Agency is a Python-based framework that auto-discovers your GitHub repositories, registers them as agency modules, routes tasks to the right module, and exposes everything through a unified CLI + FastAPI + MCP server + React dashboard.

## Features

- **Auto-Discovery**: Fetches all public repos and classifies them by category
- **Smart Routing**: Natural language tasks are routed to the best matching repo/module
- **GitHub Intelligence Scout**: Real-time trending, velocity, and hidden-gems reports
- **Unified CLI**: Rich terminal interface for managing the entire agency
- **FastAPI Server**: REST API for all operations
- **MCP Server**: Expose agency as Model Context Protocol tools
- **React Dashboard**: Interactive visualization of your repo universe

## Quick Start

```bash
# Install
pip install -e .

# Sync all your repos
opa sync

# View registry
opa registry

# Dispatch a task
opa dispatch "run voice assistant"

# Dispatch without waiting
opa dispatch "run voice assistant" --no-wait

# Check task status
opa task-status <task-id>

# Run intel scout
opa intel --type trending

# Start the general agency Telegram bot (tasks + approvals)
opa telegram-bot --token <BOT_TOKEN>

# Start the Career-Ops Telegram bot
opa telegram-career-bot --token <BOT_TOKEN>

# Start API server
opa serve

# Start MCP server
python -m sahiixx_agency.mcp_server.main
```

## Architecture

```
sahiixx-agency/
├── sahiixx_agency/        # Python package
│   ├── core/              # engine, bus, memory, registry, router, runner, security
│   ├── adapters/          # category + specialized integration layers
│   ├── cli/               # Typer + Rich CLI (entry: `opa`)
│   ├── api/               # FastAPI server
│   ├── mcp_server/        # MCP server (stdio / SSE)
│   ├── discovery/         # GitHub repo auto-discovery
│   └── telegram/         # Telegram bot
├── dashboard/             # React 19 + Vite + D3 visualization app (separate npm project)
├── config/                # agency.yaml config
├── data/                  # registry.json, repos/, task-logs (runtime, gitignored)
├── tests/                 # pytest suite
└── scripts/               # setup, sync, deploy, smoke scripts
```

## CLI Commands

| Command | Description |
|---|---|
| `opa sync` | Discover GitHub repos into the registry |
| `opa registry` | List/filter registry modules |
| `opa dispatch "<intent>"` | Dispatch an intent + payload through the engine |
| `opa do <intent words>` | Shorthand for `dispatch` (joins argv) |
| `opa exec <module>` | Clone + install + run a module directly |
| `opa task-status <id>` / `opa task-list` | Inspect dispatched tasks |
| `opa stats` | Agency summary panel |
| `opa intel --type <trending\|velocity\|hidden_gems>` | GitHub intelligence scout |
| `opa serve` | Start the FastAPI server (uvicorn) |
| `opa telegram-bot` / `opa telegram-career-bot` | Start the Telegram bots |
| `opa llm-providers` / `opa llm-chat` / `opa llm-costs` | LLM sub-app |
| `opa workflow-list` / `workflow-create` / `workflow-run` / `workflow-instances` / `workflow-resume` | Workflow engine |
| `opa notify-send` | Notifications (sse/telegram/email/webhook) |
| `opa costs` / `opa metrics` / `opa health` | Observability |
| `opa marketplace-list` / `install` / `enable` / `disable` / `rate` | Module marketplace |
| `python -m sahiixx_agency.mcp_server.main` | Start the MCP server |

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Health check |
| `/stats` | GET | Agency statistics |
| `/registry` | GET | List all modules |
| `/registry/{id}` | GET | Get module details |
| `/registry/sync` | POST | Sync repos from GitHub |
| `/tasks` | POST | Create and dispatch a task (returns pending) |
| `/tasks` | GET | List recent tasks |
| `/tasks/{id}` | GET | Get task status and result |
| `/tasks/{id}/approve` | POST | Approve a high-risk task |
| `/intel` | GET | Run intelligence scout |
| `/telegram/status` | GET | Telegram bot config status |
| `/telegram/webhook` | POST | Receive Telegram webhook updates |
| `/dashboard/graph-data` | GET | Graph data for dashboard |

## MCP Tools

- `list_modules` — List agency modules (optionally filtered by category)
- `dispatch_task` — Dispatch a task and run the worker
- `run_intel_scout` — GitHub intelligence (trending/velocity/hidden_gems)
- `agency_stats` — Get statistics
- `sync_registry` — Sync repos from GitHub
- `list_workflows` / `run_workflow` — Workflow engine access
- `send_notification` — sse/telegram/email/webhook
- `get_metrics` / `get_health` — Observability

## Environment Variables

| Variable | Description |
|---|---|
| `GITHUB_TOKEN` | GitHub personal access token (required for `opa sync`) |
| `GITHUB_USER` | GitHub username (default: sahiixx) |
| `OPA_CONFIG` | Path to agency.yaml (default: config/agency.yaml) |
| `OPA_API_KEY` | If set, all mutating API endpoints require header `X-OPA-API-Key` |
| `OPA_CORS_ORIGINS` | Comma-separated allowed CORS origins (default: local dashboard dev servers) |
| `MCP_TRANSPORT` | `stdio` (default) or `sse` |
| `MCP_HOST` / `MCP_PORT` | SSE bind host/port (default 127.0.0.1:8081) |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token (also accepted in agency.yaml) |
| `TELEGRAM_ALLOWED_CHAT_IDS` | Comma-separated allowed chat IDs (empty = allow all — not recommended) |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `OPENROUTER_API_KEY` | LLM provider keys (all optional) |

See `.env.example` for the full template.

## License

MIT
