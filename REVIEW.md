# Docs Review: Async Task Worker + Status Endpoint

## Summary

The files reviewed do **not yet implement** the async task worker feature described in the design spec (`docs/superpowers/specs/2026-06-12-async-task-worker-design.md`). The engine, API, CLI, and dashboard task-queue UI remain in their pre-feature state, with only unrelated formatting changes and a new `StatusCard` dashboard component present.

## Per-Agent Findings

### Core Agent — async task queue and worker

**Target file:** `sahiixx_agency/core/engine.py`

**What was supposed to be built:**
- A `_tasks: dict[str, AgencyTask]` index for live task lookup.
- `start_worker()` / `stop_worker()` lifecycle methods.
- A `_worker_loop()` that dequeues from `_task_queue` and calls `_execute_task()`.
- A non-blocking `dispatch()` that returns a `PENDING` task immediately.
- `get_task(task_id)` and `list_tasks(limit)` accessors.

**Current state:**
- `AgencyEngine` declares `_task_queue: asyncio.Queue[AgencyTask]` and `_running` but neither is used.
- `dispatch()` still awaits `_execute_task()` synchronously and only returns after the task finishes.
- No `_tasks` index, worker loop, or lifecycle methods exist.
- No `get_task()` / `list_tasks()` methods exist.

**Issues / inconsistencies:**
- `TaskRouter.route()` currently sets `task.status = TaskStatus.RUNNING` and `task.started_at` before returning. If the design spec is followed, the router should leave the task in `PENDING` so the worker can perform the `PENDING -> RUNNING -> COMPLETED/FAILED` transition. The Core Agent will need to coordinate this with the Router Agent or adjust `dispatch()` to reset status after routing.
- `_execute_task()` already handles `RUNNING`, success, failure, and memory logging, so the worker can reuse it with minimal changes.

### API Agent — task endpoints

**Target file:** `sahiixx_agency/api/main.py`

**What was supposed to be built:**
- Start/stop the engine worker in `lifespan`.
- `POST /tasks` accepting a structured body and returning `202 Accepted` with a `PENDING` task.
- `GET /tasks/{task_id}` for per-task status/result/error lookup.
- `GET /tasks` returning recent tasks via `engine.list_tasks()`.
- `GET /worker/status` returning `{ running: bool, queue_size: int }`.

**Current state:**
- `lifespan` initializes the engine but does not start/stop a worker.
- `POST /tasks` still takes `intent` as a query-style parameter and awaits `engine.dispatch()`, returning the completed task synchronously.
- `GET /tasks/{task_id}` and `GET /worker/status` do not exist.
- `GET /tasks` returns memory events filtered by `task.completed` rather than a task list.

**Issues / inconsistencies:**
- The current `POST /tasks` is blocking; long module runs will hold the request open and risk HTTP timeouts.
- Returning memory events from `GET /tasks` is misleading because it only shows completed tasks and uses an event schema rather than the `AgencyTask` schema.
- The worker status endpoint is not implemented, so dashboards/CLI cannot observe queue health.

### CLI Agent — task commands

**Target file:** `sahiixx_agency/cli/main.py`

**What was supposed to be built:**
- `opa submit` command for async task submission.
- `opa tasks` command listing recent tasks.
- `opa task <task_id>` command showing task details.
- Updated `opa dispatch` that polls until terminal or supports `--no-wait`.

**Current state:**
- A new `opa status` command was added (reads `pyproject.toml` and prints package info); this is unrelated to the task queue feature.
- `opa dispatch` still runs `engine.dispatch()` synchronously and blocks until completion.
- No `opa submit`, `opa tasks`, or `opa task` commands exist.

**Issues / inconsistencies:**
- Without the engine-side async worker, the CLI cannot implement polling semantics.
- The new `status` command is harmless but does not satisfy the task-status requirement.

### Dashboard Agent — task queue UI

**Target files:** `dashboard/src/components/TaskQueue.tsx`, `dashboard/src/pages/Home.tsx`

**What was supposed to be built:**
- A `TaskQueue.tsx` component polling `GET /tasks` every 3 seconds.
- Integration into `Home.tsx` below `StatsDashboard` or another sensible location.

**Current state:**
- `TaskQueue.tsx` does not exist.
- `Home.tsx` imports and renders `StatusCard` (a separate status-endpoint component), but no task queue UI.

**Issues / inconsistencies:**
- `StatusCard` fetches `/status` once on mount and never refreshes. For a live task queue, continuous polling or the planned 3-second refresh is needed.

### Tests

**Target file:** `tests/test_core.py`

**What was supposed to be built:**
- Updated `test_dispatch_task` asserting `PENDING` return and terminal polling.
- New `test_task_worker_transitions_state`.
- New `test_get_task_unknown_id`.

**Current state:**
- Tests are unchanged from the pre-feature version.
- `test_dispatch_task` asserts `task.status.value in ("running", "completed", "failed")`, which is inconsistent with the spec's `PENDING` return.

## Async Worker Semantics Assessment

Because the worker is not implemented, the following cannot be verified but can be assessed against the design:

- **Queue discipline:** Using `asyncio.Queue` with a single `_worker_loop` task gives FIFO order and serialized execution. This is correct for a first iteration but means only one task runs at a time. If modules are long-running, throughput will be limited; document this or consider a bounded worker pool later.
- **Lifecycle:** Starting the worker in FastAPI `lifespan` and stopping on shutdown is the right pattern. Ensure `stop_worker()` drains or cancels gracefully and awaits the loop task to avoid `Task was destroyed but it is pending!` warnings.
- **Status transitions:** The design spec expects `PENDING -> RUNNING -> COMPLETED/FAILED`. The current `TaskRouter.route()` sets `RUNNING` immediately, so the Core Agent must change the router or reset status in `dispatch()` to preserve the `PENDING` state.
- **Error isolation:** `_execute_task()` already catches exceptions and marks tasks `FAILED`, which keeps the worker alive. Good.
- **Cancellation:** `TaskStatus.CANCELLED` exists in the model but is unused. The design spec correctly leaves cancellation out of scope.

## Security Concerns

1. **Unbounded queue:** `asyncio.Queue()` is unbounded by default. A burst of `POST /tasks` requests can exhaust memory. Consider `asyncio.Queue(maxsize=...)` and returning `503 Service Unavailable` when full.
2. **Shell injection via payload:** `_execute_task()` passes `task.payload.get("command")` and `env` to `runner.run()`. The existing code already has this vector; the async worker does not introduce it, but it does make it easier to queue many malicious payloads quickly. Ensure `runner.run()` sanitizes commands and env vars and does not use `shell=True` with user input.
3. **No request authentication:** `POST /tasks` and `GET /tasks/{task_id}` are unauthenticated. Combined with arbitrary module execution, this is a high-risk surface. Add auth or document that the API should not be exposed publicly.
4. **Task ID enumeration:** Sequential or predictable task IDs would allow guessing other tasks' results. The router currently uses `task_{uuid.hex[:12]}`, which is acceptable.
5. **Result exposure:** `GET /tasks/{task_id}` will return `result` and `error` strings. Ensure no secrets (env vars, tokens) leak into task results.

## Suggested Follow-Ups

1. **Core Agent:** Implement `_tasks`, `start_worker()`, `stop_worker()`, `_worker_loop()`, `submit_task()` (or make `dispatch()` non-blocking per spec), `get_task()`, and `list_tasks()`. Coordinate with `TaskRouter` so tasks start as `PENDING`.
2. **API Agent:** Add worker lifecycle in `lifespan`, structured `POST /tasks` body, `202 Accepted` response, `GET /tasks/{task_id}`, `GET /worker/status`, and switch `GET /tasks` to `engine.list_tasks()`.
3. **CLI Agent:** Implement `opa submit`, `opa tasks`, `opa task`, and update `opa dispatch` to poll or support `--no-wait`.
4. **Dashboard Agent:** Create `TaskQueue.tsx` with 3-second polling and integrate it into `Home.tsx`. Consider also polling `GET /worker/status` for queue health.
5. **Tests:** Update `test_dispatch_task` and add worker/lookup tests. Add an integration test for `POST /tasks -> GET /tasks/{task_id}` through the API.
6. **Bound the queue:** Add `maxsize` to `_task_queue` and handle `QueueFull` in `submit_task()` / `POST /tasks`.
7. **Documentation:** Update `docs/superpowers/specs/2026-06-12-async-task-worker-design.md` if the final implementation deviates from the spec (e.g., if `submit_task()` is added separately from `dispatch()` as suggested in the prompt).

## Files Reviewed

- `sahiixx_agency/core/engine.py`
- `sahiixx_agency/api/main.py`
- `sahiixx_agency/cli/main.py`
- `dashboard/src/components/TaskQueue.tsx` (missing)
- `dashboard/src/pages/Home.tsx`
- `dashboard/src/components/StatusCard.tsx` (referenced)
- `tests/test_core.py`
- `sahiixx_agency/core/models.py` (for TaskStatus model support)
- `sahiixx_agency/core/router.py` (for status transition behavior)
- `docs/superpowers/specs/2026-06-12-async-task-worker-design.md` (design spec)
