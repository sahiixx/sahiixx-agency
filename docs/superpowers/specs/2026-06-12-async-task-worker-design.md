# Async Task Worker + Status Endpoint

## Goal
Make `AgencyEngine.dispatch()` non-blocking by routing tasks through an in-process `asyncio` worker queue, and expose a pollable `GET /tasks/{task_id}` endpoint (plus CLI `opa task status <id>`) so callers can observe task lifecycle.

## Context
`AgencyEngine` currently has an unused `_task_queue: asyncio.Queue[AgencyTask]` and `_running` flag. `dispatch()` executes the task inline and only returns after completion. The API has `POST /tasks` and `GET /tasks` (which lists completed memory events) but no per-task status lookup. `TaskStatus.PENDING` and `TaskStatus.CANCELLED` exist in the model but are not used.

## Approach
Use an in-memory asyncio worker. Tasks survive only for the process lifetime; restart persistence is out of scope for this change and can be added later via `AgencyMemory` if required.

### Alternatives considered
1. **Persisted task state** — write task snapshots to `AgencyMemory` on every transition so status survives restarts. Rejected because it adds I/O and complexity beyond the immediate "small feature" goal.
2. **External task queue (Celery/RQ)** — requires new infrastructure. Rejected as overkill.

## Design

### Engine changes (`sahiixx_agency/core/engine.py`)
- Add `_tasks: dict[str, AgencyTask]` to store live task snapshots.
- Add `start_worker() -> None`:
  - Set `_running = True`.
  - Create an `asyncio.Task` running `_worker_loop()`.
- Add `stop_worker() -> None`:
  - Set `_running = False`.
  - Cancel the worker task and await it.
- Add `_worker_loop() -> None`:
  - While `_running`, get from `_task_queue` with a short timeout.
  - Call `_execute_task(task)` for each dequeued task.
- Update `dispatch(intent, payload)`:
  - Route and create task with `status=TaskStatus.PENDING`.
  - Store in `_tasks`.
  - Put on `_task_queue`.
  - Log `task.created`.
  - Return task immediately.
- Update `_execute_task(task)`:
  - Set `status=RUNNING`, `started_at`.
  - Existing execution logic unchanged.
  - On success set `status=COMPLETED`, `completed_at`, `result`.
  - On exception set `status=FAILED`, `error`.
  - Log `task.running`, `task.completed`, or `task.failed`.
- Add `get_task(task_id: str) -> AgencyTask | None`.
- Add `list_tasks(limit: int = 50) -> list[AgencyTask]` returning recently created tasks from `_tasks`.

### API changes (`sahiixx_agency/api/main.py`)
- In `lifespan`:
  - `await _engine.start_worker()` after engine creation.
  - `await _engine.stop_worker()` on shutdown.
- Update `POST /tasks`:
  - Still calls `engine.dispatch(intent, payload)`.
  - Returns the pending task (same schema, `status=pending`).
- Add `GET /tasks/{task_id}`:
  - Look up via `engine.get_task(task_id)`.
  - Return 404 if not found.
- Update `GET /tasks`:
  - Return `engine.list_tasks(limit)` instead of only completed memory events.

### CLI changes (`sahiixx_agency/cli/main.py`)
- Update `opa dispatch`:
  - Start engine, dispatch task.
  - Poll `engine.get_task(task.id)` every 0.5 s until status is terminal (`completed`, `failed`, `cancelled`).
  - Print final result as today.
  - Add `--no-wait` option to return immediately with the task id and pending status.
- Add `opa task status <task_id>`:
  - Look up task and print status, timestamps, and result/error preview.

### Tests (`tests/test_core.py`)
- Update `test_dispatch_task`:
  - Dispatch returns `PENDING`.
  - Poll `engine.get_task(task.id)` until terminal or timeout.
  - Assert terminal status is `COMPLETED` or `FAILED`.
- Add `test_task_worker_transitions_state`:
  - Dispatch a task, wait for worker, assert status progression.
- Add `test_get_task_unknown_id`:
  - Assert `get_task("missing")` returns `None`.

## Error handling
- Worker loop catches exceptions inside `_execute_task`; worker itself keeps running.
- Task execution exceptions mark the task `FAILED` and store the error string.
- API returns 404 for unknown task IDs.
- CLI `opa task status` prints a friendly "not found" message and exits with code 1.

## Out of scope
- Task cancellation / retry.
- Restart persistence.
- WebSocket / SSE push notifications.
- Changing the existing `POST /tasks/{module_id}/execute` synchronous execution endpoint.

## Success criteria
- `POST /tasks` returns in < 100 ms even if the underlying module run takes seconds.
- `GET /tasks/{task_id}` returns correct state transitions (`pending` → `running` → `completed`/`failed`).
- `opa dispatch` still prints a final result, but the task is routed through the queue.
- `opa task status <id>` returns task status.
- All existing tests pass after updating expectations.
