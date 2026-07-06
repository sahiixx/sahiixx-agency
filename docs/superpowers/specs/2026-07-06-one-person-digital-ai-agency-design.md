# One Person Digital AI Agency — Design Specification

**Date:** 2026-07-06  
**Status:** Draft — awaiting review  
**Author:** Kimi Code / sahiixx  

---

## 1. Vision

A single operator controls an army of AI tools and GitHub repositories through one unified interface. The agency auto-discovers trending tools, registers them, runs them safely, remembers context across tasks, and can eventually be packaged and sold as a deployable "agency-in-a-box."

This design builds on top of the existing **One Person Agency (OPA)** scaffold at `C:/Users/sahii/sahiixx-agency`, which already has:

- 201 registered repos in `data/registry.json`
- 9 cloned repos in `data/repos/`
- Adapters for career, design, hiring, security, video
- FastAPI server, Typer CLI, MCP server, React dashboard
- Task worker, message bus, and SQLite memory

The goal is to evolve OPA from a repo orchestrator into a full digital agency operating system.

---

## 2. Success Criteria

1. A user can say or type one intent and the agency dispatches it to the best tool — whether it is one of the existing 201 repos or a repo discovered this morning.
2. Trending repos from GitHub, Hacker News, Reddit, and X are auto-discovered, classified, and registered daily.
3. Every registered repo can be executed safely with sandboxing, timeouts, approval gates, and cost controls.
4. The agency remembers context, tracks spend, and can run multi-step workflows autonomously.
5. The system can eventually be packaged and sold with multi-tenancy, white-labeling, and deployment tiers.

---

## 3. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  Interfaces: CLI • API • Dashboard • Telegram • Voice (FRIDAY)      │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Orchestrator: Intent Router • Task Worker • Memory • Approval Gates │
└─────────────────────────────────────────────────────────────────────┘
                                  │
            ┌─────────────────────┼─────────────────────┐
            ▼                     ▼                     ▼
┌───────────────┐    ┌────────────────────┐    ┌──────────────────┐
│  Your Repos   │    │  Trending Discovery │    │  MCP Tool Mesh   │
│  (201 modules)│    │  (GitHub/HN/Reddit/X)│    │  (external agents)│
└───────────────┘    └────────────────────┘    └──────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Adapters: Generic • Custom • Security • Career • Design • Video    │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.1 Design Principles

- **One intent, one dispatch.** The user never needs to know which repo is running.
- **Discover, don't hardcode.** Trending tools are pulled in automatically, not manually wired.
- **Safe by default.** Unknown repos run sandboxed with no network unless explicitly approved.
- **Extensible by protocol.** MCP is the standard interface for external agents joining the mesh.
- **Memory is not optional.** Every task, output, and human decision is logged and retrievable.

---

## 4. Discovery Feed (Real-Time Repo Discovery)

### 4.1 Sources

| Source | Mechanism | Refresh Schedule |
|--------|-----------|------------------|
| GitHub Trending | Scrape `github.com/trending` + GitHub search API fallback | Daily 06:00 UTC |
| GitHub Velocity | Search `created:>7d stars:>50` sorted by stars per language | Daily 06:00 UTC |
| Hacker News | Algolia HN API — Show HN + github.com links in stories | Daily 06:00 UTC + hourly top stories |
| Reddit | Search r/MachineLearning, r/webdev, r/LocalLLaMA, r/selfhosted for github.com URLs | Daily |
| Twitter/X | Recent tweets containing github.com links via API or Nitter fallback | Daily |
| Manual URL submission | CLI/API endpoint for one-off registration | On demand |

### 4.2 Discovery Pipeline

1. **Collect** — fetch raw repo URLs from all sources.
2. **Deduplicate** — normalize URLs; keep earliest mention and source attribution.
3. **Filter** — apply minimum stars threshold, language allowlist, blocklist, spam detection.
4. **Classify** — assign category and capabilities using keyword heuristics + LLM fallback.
5. **Register** — add to `data/registry.json` with `source: "discovery"` and metadata.
6. **Shallow Clone** — `git clone --depth 1` into `data/repos/trending/<owner>/<repo>`.
7. **Infer Entrypoint** — detect `package.json`, `main.py`, `Makefile`, `pyproject.toml`, `README.md` run instructions.
8. **Score** — relevance to agency categories; surface top N in dashboard.

### 4.3 Storage

Discovery results stored in:

- `data/registry.json` — canonical registry
- `data/discovery/<YYYY-MM-DD>.jsonl` — daily raw discovery snapshots
- `data/discovery/queue.json` — pending repos awaiting classification or approval

---

## 5. Execution Layer

### 5.1 Adapter Types

| Adapter | Use Case |
|---------|----------|
| **Generic Adapter** | Auto-runs Python/Node/Docker/Make repos using inferred entrypoint |
| **Custom Adapters** | Special semantics: `html-anything`, `t3mp3st`, `career-ops`, `hiring-agent`, `open-montage` |
| **Security Adapter** | Sandboxed red-team tools with approval gates |
| **MCP Adapter** | Exposes a repo as an MCP tool/server |

### 5.2 Generic Adapter Behavior

1. Inspect repo for recognizable entrypoint:
   - `package.json` → run `npm install && npm run <script>`
   - `pyproject.toml` / `requirements.txt` → run `pip install -e . && python <main>.py`
   - `Makefile` → run `make <target>`
   - `Dockerfile` → run `docker build && docker run`
   - `README.md` → parse "Quick Start" / "Usage" section with LLM
2. Run in subprocess with timeout, env injection, and sandbox.
3. Capture stdout, stderr, generated files, and return structured result.
4. Fallback to simulation if repo fails or is unsafe.

### 5.3 Sandboxing

- Subprocess timeout (default 120s, configurable).
- Network egress disabled by default for unknown repos.
- CPU/memory limits via job objects on Windows / cgroups on Linux.
- Temporary working directories; persistent output copied to `data/outputs/<task_id>/`.
- Dependency vulnerability scan before install (optional, via `pip-audit`, `npm audit`).

### 5.4 Approval Gates

Require explicit approval for:

- Network egress beyond localhost
- Writing outside `data/` or designated output dirs
- Spending money (API calls, cloud resources)
- Security/post-exploitation tools
- Posting to social accounts or sending emails

Approval methods:

- Dashboard approval queue
- Telegram `/approve <task_id>`
- Time-bounded auto-approval tokens for trusted tools

---

## 6. Memory & Context

### 6.1 Memory Stores

| Store | Purpose |
|-------|---------|
| Task History | Every dispatched task, payload, result, logs |
| Conversation Threads | Chat/Telegram sessions tied to task IDs |
| Project Memory | Per-client or per-campaign state |
| RAG Index | READMEs, docs, generated outputs for semantic search |
| Long-Term Memory | Titans / Letta integration for agent continuity |

### 6.2 Memory Usage

- Router uses task history to improve intent matching.
- Adapters retrieve project context before execution.
- Workflows resume from last known state after restart.
- RAG answers "which tool did I use for X last week?"

---

## 7. LLM Abstraction

### 7.1 Providers

- OpenAI (GPT-4o, GPT-4o-mini)
- Anthropic (Claude 3.5/4 Sonnet)
- Google (Gemini 1.5 Pro/Flash)
- Local: Ollama, LM Studio, vLLM

### 7.2 Model Selection

| Task Type | Default Model |
|-----------|---------------|
| Coding / reasoning | Claude Sonnet |
| Creative / long-form | Claude Sonnet or GPT-4o |
| Summarization | GPT-4o-mini or Gemini Flash |
| Classification | GPT-4o-mini |
| Local / private | Ollama Llama 3.1 |

### 7.3 Cost Tracking

- Log every LLM call with model, tokens, estimated cost.
- Per-task and per-day spend caps.
- Alert when approaching budget.

---

## 8. Autonomous Workflows

### 8.1 Building Blocks

- **Scheduler** — recurring jobs via `schedule` + APScheduler.
- **Event Bus** — existing in-memory pub/sub extended with persistent queue.
- **Webhooks** — ingest GitHub, Telegram, Stripe, form submissions.
- **State Machines** — multi-step workflows with explicit states and retries.
- **Human Gates** — pause workflows pending approval.

### 8.2 Example Workflows

1. **Trending Content Pipeline**
   - Trigger: daily at 06:30 UTC
   - Steps: discover repos → filter top 10 → summarize → generate social thread → queue post → human approve → publish

2. **Hiring Pipeline**
   - Trigger: new resume PDF uploaded
   - Steps: parse → score → rank → draft outreach → human approve → send email

3. **Idea-to-Landing-Page**
   - Trigger: user says "build a landing page for X"
   - Steps: research → write brief → dispatch html-anything → verify server → return link

4. **Security Scan**
   - Trigger: weekly or new target submitted
   - Steps: validate scope → recon → propose exploits → human approve intrusive steps → report

---

## 9. Multi-Modal I/O

| Mode | Input | Output |
|------|-------|--------|
| Text | CLI, API, Telegram | Text, structured JSON |
| Voice | FRIDAY OS microphone | Spoken responses, text transcript |
| Image | Uploads, screenshots | Generated images, annotated outputs |
| Video | Uploads, screen recordings | Generated videos, clips |
| Files | PDF, CSV, DOCX | Reports, transformed files |
| Browser | Screen control / browser agent | Actions, extracted data |

---

## 10. Human-in-the-Loop

- Dashboard approval queue with one-click approve/reject/retry.
- Telegram bot sends actionable notifications: `Task X needs approval. /approve X /reject X`.
- Auto-approval policies configurable per tool and per risk level.
- Audit log records who approved what and when.

---

## 11. Notifications

- Telegram bot alerts for task completion, failures, approvals needed.
- Email digest: daily summary of completed tasks, discovered repos, spend.
- Dashboard notifications with real-time WebSocket/SSE.
- Webhook callbacks to external CRMs, Slack, Notion.

---

## 12. Observability

- Structured JSON logs per task.
- Metrics exposed at `/metrics`:
  - tasks/min
  - success/failure/timeout rates
  - adapter latency
  - LLM spend and token usage
  - discovery count per source
- Health checks for API, worker, adapters, external services.
- Distributed tracing across multi-step workflows.

---

## 13. Multi-Tenancy & Packaging

### 13.1 Deployment Tiers

| Tier | Target |
|------|--------|
| Solo | Single user, local SQLite, Docker Compose |
| Team | Multiple users, Postgres, shared registry, role-based access |
| Enterprise | Kubernetes, SSO, audit compliance, custom adapters |

### 13.2 Isolation

- Each project/client gets separate namespace in `data/projects/<project_id>/`.
- Per-project secrets and environment variables.
- Per-project cost tracking.

### 13.3 White-Label

- Configurable brand name, logo, colors.
- Custom domain support.
- Plugin marketplace for curated adapters.

---

## 14. Security

- Secrets loaded from environment variables only; never committed.
- Network egress controls per task.
- Sandboxed execution for unknown repos.
- Dependency vulnerability scanning before install.
- Immutable audit logs.
- RBAC for multi-user deployments.

---

## 15. Marketplace (Future)

- Curated "agency packs": content studio, security firm, recruiting agency, real estate agency.
- Community adapters with ratings and install counts.
- Paid plugin discovery integrated into the discovery feed.

---

## 16. Testing Strategy

| Layer | Tests |
|-------|-------|
| Discovery | Mocked GitHub/HN/Reddit APIs; dedupe + classify accuracy |
| Router | Intent-to-module mapping; fallback behavior |
| Adapters | Generic adapter for Python/Node/Docker/Make; custom adapter unit tests |
| API | FastAPI TestClient for `/dispatch`, `/tasks`, `/registry` |
| Workflows | In-memory bus + mocked adapters; state machine transitions |
| Integration | End-to-end: discover → register → dispatch → result |
| Load | Concurrent task workers; memory leak checks |

---

## 17. Implementation Phases

| Phase | Focus | Deliverable |
|-------|-------|-------------|
| **Phase 1 — Command Center** | Generic adapter, discovery feed, dashboard trending panel, approval gates | Working OPA that runs any repo |
| **Phase 2 — Federation** | MCP gateway, memory layer, LLM abstraction, workflow engine | Agents call each other; multi-step automations |
| **Phase 3 — Autonomy + Product** | Scheduling, webhooks, multi-tenancy, packaging, marketplace | Sellable agency-in-a-box |

---

## 18. Open Questions

1. Should discovered repos be auto-cloned or only registered until first use?
2. What is the monthly budget cap for auto-discovered repo execution?
3. Should multi-tenancy use Postgres from Phase 2 or stay SQLite until Phase 3?
4. Which interface should be primary: CLI, Telegram, or dashboard?

---

## 19. Next Step

After this spec is approved, invoke the `writing-plans` skill to create a detailed Phase 1 implementation plan.
