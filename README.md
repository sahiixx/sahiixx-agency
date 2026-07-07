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
opa task status <task-id>

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
├── core/           # Orchestration engine, bus, memory
├── registry/       # Auto-generated repo manifests
├── adapters/       # Category-specific integration layers
├── cli/            # Rich CLI (typer + rich)
├── api/            # FastAPI server
├── mcp_server/     # MCP server for external tools
├── dashboard/      # React visualization app
├── config/         # Agency YAML config
└── scripts/        # Setup, sync, deploy scripts
```

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

- `list_modules` — List agency modules
- `dispatch_task` — Dispatch a task
- `run_intel_scout` — GitHub intelligence
- `agency_stats` — Get statistics
- `sync_registry` — Sync repos

## Environment Variables

| Variable | Description |
|---|---|
| `GITHUB_TOKEN` | GitHub personal access token |
| `GITHUB_USER` | GitHub username (default: sahiixx) |
| `OPA_CONFIG` | Path to agency.yaml |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token (also accepted in agency.yaml) |
| `TELEGRAM_ALLOWED_CHAT_IDS` | Comma-separated list of allowed Telegram chat IDs |

## License

MIT
