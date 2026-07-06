# Real Phase 1 — Agency Command Center Implementation Plan

> **Goal:** Build the actual unified interface for the One Person Digital AI Agency. Not backend plumbing. The product.

## What "done" looks like

A user can:
1. Open the dashboard and see a **chat input** as the primary interface.
2. Type "build me a landing page for Pulse AI wristband" and the agency dispatches, runs, and returns a result.
3. See a **task stream** of running/completed tasks.
4. See **trending repos** with one-click dispatch.
5. See **pending approvals** and approve/reject them.
6. Use the CLI: `opa "build me a landing page"` and get the same result.
7. Use Telegram: send the same message to the bot and get the result.

## Global Constraints

- Target Python 3.10+ syntax; use `from __future__ import annotations`.
- Line length 120.
- All domain models are Pydantic v2 BaseModel.
- Async core engine and API.
- Tests must use monkeypatch, not real network calls or real subprocesses.
- Every task ends with green pytest, clean ruff, clean mypy.
- Dashboard uses React 19 + TypeScript + Vite + Tailwind.
- Commit after each task.

---

## Task 1: Chat-First Dashboard Shell

Replace the AI Nexus graph with a chat-first agency workspace.

**Files:**
- Create: `dashboard/src/pages/Agency.tsx`
- Modify: `dashboard/src/App.tsx` — add `/agency` route, make it default
- Modify: `dashboard/src/components/Layout.tsx` — agency sidebar with Tasks, Discovery, Approvals, Memory

**Layout:**
- Left sidebar: Agency logo, nav items (Tasks, Discovery, Approvals, Memory, Settings).
- Center: Chat thread (messages from user and agency).
- Bottom of center: Chat input with send button.
- Right panel: Context-aware (trending repos, task details, approval queue).

- [ ] Step 1: Create `Agency.tsx` with basic layout (sidebar, chat area, input).
- [ ] Step 2: Add route to `App.tsx`, make `/agency` the default route.
- [ ] Step 3: Verify build: `cd dashboard && npm run build`.
- [ ] Step 4: Commit.

---

## Task 2: Chat API + Message History

Backend support for chat messages and task results.

**Files:**
- Modify: `sahiixx_agency/core/models.py` — add `ChatMessage` model.
- Modify: `sahiixx_agency/core/memory.py` — add `get_conversation(thread_id)` and `add_message`.
- Modify: `sahiixx_agency/api/main.py` — add `POST /chat` and `GET /chat/{thread_id}`.
- Test: `tests/test_chat.py`.

**Interfaces:**
- `POST /chat` — body: `{ "message": "build me a landing page", "thread_id": "optional" }`. Returns `{ thread_id, task_id, status }`.
- `GET /chat/{thread_id}` — returns list of messages in the thread.

- [ ] Step 1: Write failing test for `POST /chat`.
- [ ] Step 2: Add `ChatMessage` model.
- [ ] Step 3: Add memory methods for conversation.
- [ ] Step 4: Add `/chat` endpoints.
- [ ] Step 5: Run tests, lint, type check.
- [ ] Step 6: Commit.

---

## Task 3: Dashboard Chat Component

Wire the dashboard chat to the backend.

**Files:**
- Create: `dashboard/src/components/chat/ChatThread.tsx`
- Create: `dashboard/src/components/chat/ChatInput.tsx`
- Modify: `dashboard/src/pages/Agency.tsx` — integrate chat components.

**Behavior:**
- User types message, hits send.
- POST to `/chat`, get task_id.
- Poll `GET /tasks/{task_id}` every 2s until completed.
- Display task result as a chat message from the agency.
- Store message history in local state (thread_id from first response).

- [ ] Step 1: Create `ChatThread.tsx` — renders messages, auto-scrolls.
- [ ] Step 2: Create `ChatInput.tsx` — input + send button, calls `/chat`.
- [ ] Step 3: Integrate into `Agency.tsx`.
- [ ] Step 4: Verify build.
- [ ] Step 5: Commit.

---

## Task 4: Task Stream Panel

Show running, pending, and completed tasks in the dashboard.

**Files:**
- Create: `dashboard/src/components/tasks/TaskStream.tsx`
- Modify: `dashboard/src/pages/Agency.tsx` — show task stream in sidebar or right panel.
- Modify: `sahiixx_agency/api/main.py` — add `GET /tasks/stream` (SSE or polling).

**Behavior:**
- Poll `GET /tasks` every 3s.
- Show task list: intent, status, module, time.
- Click a task to see details in right panel.
- Show approval-needed tasks with approve/reject buttons.

- [ ] Step 1: Add `GET /tasks` polling endpoint (already exists, verify it works).
- [ ] Step 2: Create `TaskStream.tsx` with task cards.
- [ ] Step 3: Integrate into `Agency.tsx`.
- [ ] Step 4: Verify build.
- [ ] Step 5: Commit.

---

## Task 5: Approval Queue UI

Show pending approvals in the dashboard with one-click actions.

**Files:**
- Create: `dashboard/src/components/approvals/ApprovalQueue.tsx`
- Modify: `sahiixx_agency/api/main.py` — add `GET /approvals/pending` and `POST /approvals/{id}/approve`.
- Modify: `dashboard/src/pages/Agency.tsx` — add Approvals nav item.

**Behavior:**
- Poll `GET /approvals/pending` every 5s.
- Show approval cards: task intent, risk level, reason.
- Approve button → `POST /approvals/{id}/approve`.
- Reject button → `POST /approvals/{id}/reject`.

- [ ] Step 1: Add `/approvals/pending` endpoint.
- [ ] Step 2: Add `/approvals/{id}/approve` and `/reject` endpoints.
- [ ] Step 3: Create `ApprovalQueue.tsx`.
- [ ] Step 4: Integrate into `Agency.tsx`.
- [ ] Step 5: Verify build.
- [ ] Step 6: Commit.

---

## Task 6: Natural-Language CLI

Make `opa` accept natural language directly.

**Files:**
- Modify: `sahiixx_agency/cli/main.py` — add `opa chat "message"` or `opa "message"`.

**Behavior:**
- `opa "build me a landing page"` → calls `POST /chat` → polls task → prints result.
- `opa chat "message"` — same.
- Rich output: task status, stdout, links.

- [ ] Step 1: Add CLI command that accepts a string argument.
- [ ] Step 2: POST to `/chat`, poll task, print result with Rich tables.
- [ ] Step 3: Test with `opa "build me a landing page"`.
- [ ] Step 4: Commit.

---

## Task 7: Telegram Bot Integration

Wire the existing Telegram bot to the chat API.

**Files:**
- Modify: `sahiixx_agency/adapters/career/telegram_dispatcher.py` (or create new `telegram_bot.py`).
- Modify: `sahiixx_agency/cli/main.py` — add `opa telegram-bot` command to start the bot.

**Behavior:**
- User sends message to Telegram bot.
- Bot calls `POST /chat` with the message.
- Bot polls task and sends result back to user.
- Bot sends approval requests with inline approve/reject buttons.

- [ ] Step 1: Create `telegram_bot.py` that listens for messages.
- [ ] Step 2: On message, call `/chat` API and poll task.
- [ ] Step 3: Send result back to user.
- [ ] Step 4: Add `opa telegram-bot` CLI command.
- [ ] Step 5: Test with a real Telegram message.
- [ ] Step 6: Commit.

---

## Task 8: Final Integration and Verification

Ensure everything works end-to-end.

**Files:**
- All of the above.

**Verification:**
- Dashboard build passes.
- API tests pass.
- CLI test passes.
- End-to-end: type message in dashboard → task runs → result appears.
- End-to-end: type message in CLI → task runs → result prints.
- End-to-end: type message in Telegram → task runs → result comes back.

- [ ] Step 1: Run full test suite.
- [ ] Step 2: Run dashboard build.
- [ ] Step 3: Run end-to-end smoke test via dashboard.
- [ ] Step 4: Run end-to-end smoke test via CLI.
- [ ] Step 5: Commit and push.

---

## Open Questions

1. Should the old AI Nexus graph be preserved as a separate route (`/graph`) or removed entirely?
2. Should the chat use WebSocket/SSE for real-time updates, or is polling sufficient for Phase 1?
3. Should the Telegram bot be a separate process or part of the main API worker?

## Recommendation

- Preserve the old graph at `/graph` for nostalgia/reference.
- Use polling for Phase 1; upgrade to SSE/WebSocket in Phase 2.
- Telegram bot as a separate CLI command (`opa telegram-bot`) for now.
