# One Person Digital AI Agency — Phased Implementation Plan

**Date:** 2026-07-06
**Status:** Active — Phase 1 foundation exists, needs completion

---

## What Exists Right Now (As-Is)

### Backend (Partial)
| Component | Status | Notes |
|-----------|--------|-------|
| Discovery feed (GitHub/HN/Reddit) | ✅ | Sources, pipeline, classification, scoring |
| Generic adapter | ✅ | Entrypoint inference, sequential execution, fallback |
| Custom adapters (html-anything, t3mp3st, career-ops, hiring, video) | ✅ | Specialized handling |
| Task worker + router | ✅ | Intent routing, task queue, execution |
| Approval manager (stub) | ✅ | In-memory, no persistence |
| API endpoints (registry, tasks, dispatch, discovery) | ✅ | Partial |
| Memory (SQLite) | ✅ | Event log only, no conversation threads |
| Message bus | ✅ | In-memory pub/sub |

### Frontend (Minimal)
| Component | Status | Notes |
|-----------|--------|-------|
| AI Nexus graph dashboard | ✅ | Old visualization, preserved at `/graph` |
| Agency command center shell | ✅ | Chat UI, sidebar, task stream, approval queue — **not wired to real API** |
| Trending panel | ✅ | Shows discovered repos, dispatch button |

### Interfaces (Missing)
| Component | Status | Notes |
|-----------|--------|-------|
| Natural-language CLI | ❌ | `opa "do X"` not implemented |
| Telegram bot | ❌ | No bot integration |
| Voice (FRIDAY) | ❌ | Not started |
| Chat API | ❌ | No `/chat` endpoint |
| Approval queue API | ❌ | No `/approvals` endpoints |
| Task stream API | ❌ | No SSE/polling for live tasks |

### Advanced Features (Not Started)
| Component | Status | Notes |
|-----------|--------|-------|
| LLM abstraction | ❌ | No pluggable providers, no cost tracking |
| Autonomous workflows | ❌ | No scheduler, no state machines |
| Notifications | ❌ | No Telegram alerts, no email, no webhooks |
| Observability | ❌ | No metrics, no tracing |
| Multi-tenancy | ❌ | No user isolation |
| Security hardening | ❌ | No network sandbox, no dependency scanning |
| Marketplace | ❌ | Future phase |

---

## Phase 1: Complete the Command Center (Current Priority)

**Goal:** Make the agency actually usable — a single operator can type an intent and the agency runs it.

### 1.1 Chat API + Message History (Backend)
- `POST /chat` — accept natural language, dispatch task, return thread_id + task_id
- `GET /chat/{thread_id}` — return conversation history
- `ChatMessage` model — role (user/agency), content, timestamp, task_id
- Memory integration — store/retrieve conversations

### 1.2 Approval Queue API (Backend)
- `GET /approvals/pending` — list pending approvals
- `POST /approvals/{id}/approve` — approve + re-queue task
- `POST /approvals/{id}/reject` — reject task
- Wire into engine worker loop — auto-check approval before execution

### 1.3 Task Stream API (Backend)
- `GET /tasks/stream` — SSE endpoint for live task updates
- Or enhance `GET /tasks` with query params (status, limit, since)

### 1.4 Wire Dashboard to Real API (Frontend)
- Chat input → `POST /chat` → poll task → display result
- Task stream → poll `GET /tasks` → live updates
- Approval queue → poll `GET /approvals/pending` → approve/reject
- Trending panel → `GET /discovery/trending` (already exists)

### 1.5 Natural-Language CLI
- `opa "build me a landing page"` → calls `POST /chat` → polls → prints result
- `opa tasks` → list recent tasks
- `opa approve <task-id>` → approve pending task
- Rich output with tables, status colors, links

### 1.6 Telegram Bot
- `/start` — welcome message
- Any text message → `POST /chat` → poll → reply with result
- Approval requests → inline keyboard with Approve/Reject
- `/tasks` — list recent tasks
- `/status <task-id>` — check task status

### 1.7 Verification
- End-to-end: dashboard chat → task runs → result appears
- End-to-end: CLI `opa "do X"` → task runs → result prints
- End-to-end: Telegram message → task runs → bot replies
- All tests pass, ruff clean, mypy clean, dashboard build succeeds

---

## Phase 2: Intelligence Layer

**Goal:** Add LLM abstraction, memory, and autonomous workflows.

### 2.1 LLM Abstraction
- `LLMProvider` interface — OpenAI, Anthropic, Google, Ollama, LM Studio
- `LLMClient` — unified API for chat.completions
- Cost tracking per request (model, tokens, cost)
- Default model per task type (coding, creative, summarization, reasoning)
- Prompt versioning and A/B testing framework

### 2.2 Enhanced Memory
- Conversation threads with context window management
- Project-level memory (per-client, per-campaign)
- RAG over repo READMEs, docs, generated outputs
- Long-term memory via Titans or Letta integration

### 2.3 Autonomous Workflows
- Scheduler (APScheduler) for recurring tasks
- Event-driven pipelines on message bus
- Webhook ingestion (GitHub, Telegram, Stripe, forms)
- Multi-step state machines with retry and human approval
- Example workflows:
  - Daily: discover repos → summarize → generate social thread → queue post
  - Trigger: new resume PDF → parse → score → draft outreach → send
  - Trigger: user says "build landing page" → research → wireframe → generate → deploy

### 2.4 MCP Gateway
- Expose each adapter as an MCP tool
- Tool discovery endpoint
- MCP server for external clients (Claude, Cursor, Letta)

---

## Phase 3: Production Hardening

**Goal:** Make it deployable, observable, and sellable.

### 3.1 Notifications
- Telegram bot alerts (task completion, failures, approvals needed)
- Email digests (daily summary)
- Dashboard notifications (real-time SSE)
- Webhook callbacks to external CRMs, Slack, Notion

### 3.2 Observability
- Structured JSON logs per task
- Metrics: tasks/min, success/failure/timeout rates, adapter latency, LLM cost
- Health checks for API, worker, adapters, external services
- Distributed tracing across multi-step workflows
- `/metrics` endpoint for Prometheus

### 3.3 Security
- Network egress controls (blocklist/allowlist per task)
- Sandboxed execution (Docker, gVisor, or Firecracker)
- Dependency vulnerability scanning (pip-audit, npm audit)
- Secrets rotation and encryption at rest
- RBAC for multi-user deployments

### 3.4 Multi-Tenancy
- User/project isolation
- Per-project secrets and environment variables
- Per-project cost tracking
- White-label dashboard (brand, logo, colors)
- License tiers: solo, team, enterprise

### 3.5 Packaging
- Docker Compose for solo deployment
- Kubernetes manifests for team/enterprise
- Helm chart
- One-click deploy buttons (Railway, Render, Fly.io)

---

## Phase 4: Ecosystem (Future)

**Goal:** Turn the agency into a platform.

### 4.1 Marketplace
- Curated tool packs (content studio, security firm, recruiting agency, real estate)
- Community adapters with ratings and install counts
- Paid plugin discovery integrated into discovery feed

### 4.2 Voice & Multi-Modal
- FRIDAY OS integration (voice commands)
- Image/video input and output
- File uploads (PDFs, CSVs, designs)
- Screen/browser control for agentic tasks

### 4.3 Advanced AI
- Fine-tuned models for agency tasks
- Auto-prompt optimization
- Self-improving workflows (agent learns from feedback)

---

## Current Blockers

1. **Dashboard UI is not wired to real API** — chat, tasks, approvals are mock/placeholder
2. **No `/chat` endpoint** — natural language dispatch doesn't exist
3. **No `/approvals` endpoints** — approval queue UI has no backend
4. **CLI is basic** — no natural language, no rich output
5. **Telegram bot is career-ops only** — not a general agency interface

---

## Next Action

Execute **Phase 1.1-1.7** to make the agency actually usable.
