# Async Task Worker + Status Endpoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `AgencyEngine.dispatch()` non-blocking by routing tasks through an in-process `asyncio` worker queue, and expose a pollable `GET /tasks/{task_id}` endpoint plus CLI `opa task status <id>`.

**Architecture:** An `asyncio.Queue[AgencyTask]` inside `AgencyEngine` is consumed by a single background worker task. `dispatch()` enqueues a task with `status=PENDING` and returns immediately. The worker transitions tasks through `RUNNING` → `COMPLETED`/`FAILED` while storing live snapshots in an in-memory dict. FastAPI lifespan starts/stops the worker; the CLI polls status after dispatch.

**Tech Stack:** Python 3.12, asyncio, FastAPI, Typer, Rich, pytest-asyncio, Pydantic.

---

## File structure

| File | Responsibility |
|---|---|
| `sahiixx_agency/core/engine.py` | Worker lifecycle, task store, queue-driven dispatch, status lookup. |
| `sahiixx_agency/core/router.py` | Create tasks with `PENDING` status instead of `RUNNING` so the worker owns lifecycle transitions. |
| `sahiixx_agency/api/main.py` | Start/stop worker in lifespan; add `GET /tasks/{task_id}`; update `GET /tasks` to list live tasks. |
| `sahiixx_agency/cli/main.py` | Poll after `opa dispatch`; add `opa task status <id>` and `--no-wait` flag. |
| `tests/test_core.py` | Core engine + worker tests. |
| `tests/test_api.py` | FastAPI endpoint tests (new file). |
| `tests/test_cli.py` | CLI command tests (new file). |

---

### Task 1: Core engine worker + task store

**Files:**
- Modify: `sahiixx_agency/core/router.py:61-62`
- Modify: `sahiixx_agency/core/engine.py:18-123`
- Test: `tests/test_core.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_core.py`:

```python
@pytest.mark.asyncio
async def test_dispatch_returns_pending_and_worker_completes(engine):
    await engine.start_worker()
    try:
        await engine.sync_repos("sahiixx")
        task = await engine.dispatch("run voice assistant")
        assert task.status.value == "pending"
        # Poll until terminal (timeout protects against hangs)
        for _ in range(40):
            current = engine.get_task(task.id)
            assert current is not None
            if current.status.value in ("completed", "failed"):
                break
            await asyncio.sleep(0.25)
        final = engine.get_task(task.id)
        assert final.status.value in ("completed", "failed")
    finally:
        await engine.stop_worker()
```

Add `import asyncio` at the top of `tests/test_core.py` if not already present.

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
source .venv/Scripts/activate
python -m pytest tests/test_core.py::test_dispatch_returns_pending_and_worker_completes -v
```

Expected: FAIL because `start_worker`, `stop_worker`, and `get_task` do not exist, or task status is not `pending`.

- [ ] **Step 3: Change router to set PENDING status**

In `sahiixx_agency/core/router.py`, replace:

```python
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now(timezone.utc)
```

with:

```python
        task.status = TaskStatus.PENDING
```

Leave `task.started_at` as `None` until the worker starts execution.

- [ ] **Step 4: Implement engine worker, task store, and status methods**

Replace the `AgencyEngine` constructor and methods in `sahiixx_agency/core/engine.py` with the following changes. Keep all existing imports.

Constructor changes (`__init__`):

```python
        self._running = False
        self._worker_task: asyncio.Task[Any] | None = None
        self._task_queue: asyncio.Queue[AgencyTask] = asyncio.Queue()
        self._tasks: dict[str, AgencyTask] = {}
```

Add these methods after `__init__`:

```python
    async def start_worker(self) -> None:
        """Start the background task worker."""
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())

    async def stop_worker(self) -> None:
        """Stop the background task worker."""
        if not self._running:
            return
        self._running = False
        if self._worker_task is not None:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None

    async def _worker_loop(self) -> None:
        """Consume tasks from the queue and execute them."""
        while self._running:
            try:
                task = await asyncio.wait_for(self._task_queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            await self._execute_task(task)

    def get_task(self, task_id: str) -> AgencyTask | None:
        """Return the current snapshot of a task by id."""
        return self._tasks.get(task_id)

    def list_tasks(self, limit: int = 50) -> list[AgencyTask]:
        """Return recently created tasks ordered by creation time descending."""
        sorted_tasks = sorted(self._tasks.values(), key=lambda t: t.created_at, reverse=True)
        return sorted_tasks[:limit]
```

Update `dispatch()`:

```python
    async def dispatch(self, intent: str, payload: dict[str, Any] | None = None) -> AgencyTask:
        """Dispatch a task through the agency."""
        task = await self.router.route(intent, payload)
        self._tasks[task.id] = task
        self.memory.log_event("task.created", {"task_id": task.id, "intent": intent})
        await self._task_queue.put(task)
        return task
```

- [ ] **Step 5: Run test to verify it passes**

Run:
```bash
source .venv/Scripts/activate
python -m pytest tests/test_core.py::test_dispatch_returns_pending_and_worker_completes -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add sahiixx_agency/core/engine.py sahiixx_agency/core/router.py tests/test_core.py
git commit -m "feat(core): async task worker with pending status and task store"
```

---

### Task 2: Engine status lookup tests + update existing dispatch test

**Files:**
- Modify: `tests/test_core.py`

- [ ] **Step 1: Update existing dispatch test**

Replace `test_dispatch_task` in `tests/test_core.py` with:

```python
@pytest.mark.asyncio
async def test_dispatch_task(engine):
    await engine.start_worker()
    try:
        await engine.sync_repos("sahiixx")
        task = await engine.dispatch("run voice assistant")
        assert task.id is not None
        assert task.status.value == "pending"
        # Poll for terminal status
        for _ in range(40):
            current = engine.get_task(task.id)
            if current.status.value in ("completed", "failed"):
                break
            await asyncio.sleep(0.25)
        final = engine.get_task(task.id)
        assert final.status.value in ("completed", "failed")
    finally:
        await engine.stop_worker()
```

- [ ] **Step 2: Add status lookup tests**

Append to `tests/test_core.py`:

```python
@pytest.mark.asyncio
async def test_get_task_unknown_id(engine):
    assert engine.get_task("task_does_not_exist") is None


@pytest.mark.asyncio
async def test_list_tasks_returns_recent_tasks(engine):
    await engine.start_worker()
    try:
        await engine.sync_repos("sahiixx")
        task1 = await engine.dispatch("run voice assistant")
        task2 = await engine.dispatch("run voice assistant")
        tasks = engine.list_tasks(limit=10)
        ids = {t.id for t in tasks}
        assert task1.id in ids
        assert task2.id in ids
    finally:
        await engine.stop_worker()
```

- [ ] **Step 3: Run all core tests**

Run:
```bash
source .venv/Scripts/activate
python -m pytest tests/test_core.py -v
```

Expected: 7+ tests pass.

- [ ] **Step 4: Commit**

```bash
git add tests/test_core.py
git commit -m "test(core): update dispatch test and add task lookup tests"
```

---

### Task 3: API lifespan + status endpoint

**Files:**
- Modify: `sahiixx_agency/api/main.py:62-77`, `sahiixx_agency/api/main.py:158-169`
- Create: `tests/test_api.py`

- [ ] **Step 1: Write the failing API test**

Create `tests/test_api.py`:

```python
"""Tests for the FastAPI server."""

from __future__ import annotations

import asyncio
import time

import pytest
from fastapi.testclient import TestClient

from sahiixx_agency.api.main import app, get_engine
from sahiixx_agency.core.engine import AgencyEngine
from sahiixx_agency.core.models import AgencyConfig


@pytest.fixture
def client(tmp_path):
    config = AgencyConfig(data_dir=str(tmp_path))
    engine = AgencyEngine(config)

    async def _start() -> None:
        await engine.sync_repos("sahiixx")
        await engine.start_worker()

    asyncio.run(_start())

    app.dependency_overrides[get_engine] = lambda: engine
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        asyncio.run(engine.stop_worker())


def test_create_task_returns_pending(client):
    response = client.post("/tasks", params={"intent": "run voice assistant"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending"
    assert data["id"].startswith("task_")


def test_get_task_status_flow(client):
    create = client.post("/tasks", params={"intent": "run voice assistant"})
    task_id = create.json()["id"]

    for _ in range(40):
        resp = client.get(f"/tasks/{task_id}")
        status = resp.json()["status"]
        if status in ("completed", "failed"):
            break
        time.sleep(0.25)

    assert status in ("completed", "failed")


def test_get_task_not_found(client):
    resp = client.get("/tasks/task_does_not_exist")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
source .venv/Scripts/activate
python -m pytest tests/test_api.py -v
```

Expected: FAIL because `GET /tasks/{task_id}` does not exist and lifespan does not start the worker.

- [ ] **Step 3: Wire worker into lifespan and add status endpoint**

In `sahiixx_agency/api/main.py`, update the `lifespan` context manager:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _engine
    config_path = os.environ.get("OPA_CONFIG", "./config/agency.yaml")
    config = AgencyConfig()
    if os.path.exists(config_path):
        import yaml
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        config = AgencyConfig.model_validate(data)
    _engine = AgencyEngine(config)
    await _engine.start_worker()
    # Auto-sync on startup if registry is empty
    if not _engine.registry.modules:
        await _engine.sync_repos(config.github_username)
    yield
    await _engine.stop_worker()
    _engine = None
```

Update `GET /tasks` and add `GET /tasks/{task_id}`:

```python
@app.get("/tasks")
async def list_tasks(limit: int = Query(50, ge=1, le=200)) -> list[dict[str, Any]]:
    tasks = get_engine().list_tasks(limit=limit)
    return [t.model_dump(mode="json") for t in tasks]


@app.get("/tasks/{task_id}")
async def get_task(task_id: str) -> dict[str, Any]:
    task = get_engine().get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.model_dump(mode="json")
```

Remove the old `list_tasks` implementation that reads memory events.

- [ ] **Step 4: Run API tests**

Run:
```bash
source .venv/Scripts/activate
python -m pytest tests/test_api.py -v
```

Expected: PASS (may take up to ~10 s for each task run).

- [ ] **Step 5: Commit**

```bash
git add sahiixx_agency/api/main.py tests/test_api.py
git commit -m "feat(api): start worker in lifespan and add GET /tasks/{task_id}"
```

---

### Task 4: CLI dispatch polling + task status command

**Files:**
- Modify: `sahiixx_agency/cli/main.py:134-158`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write the failing CLI test**

Create `tests/test_cli.py`:

```python
"""Tests for the Typer CLI."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from sahiixx_agency.cli.main import app


runner = CliRunner()


def test_dispatch_command_returns_task_id():
    result = runner.invoke(app, ["dispatch", "run voice assistant", "--no-wait"])
    assert result.exit_code == 0
    assert "task_" in result.stdout
    assert "pending" in result.stdout


def test_task_status_unknown_id():
    result = runner.invoke(app, ["task", "status", "task_does_not_exist"])
    assert result.exit_code == 1
    assert "not found" in result.stdout.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
source .venv/Scripts/activate
python -m pytest tests/test_cli.py -v
```

Expected: FAIL because `--no-wait` and `task` subcommand do not exist.

- [ ] **Step 3: Add CLI task command group and update dispatch**

First, add a Typer sub-command group for `task` near the top of `sahiixx_agency/cli/main.py`, after the `app` definition:

```python
task_app = typer.Typer(
    name="task",
    help="Inspect and manage agency tasks",
    rich_markup_mode="rich",
)
app.add_typer(task_app)
```

Update the `dispatch` command (`sahiixx_agency/cli/main.py:134-158`) to:

```python
@app.command()
def dispatch(
    intent: str = typer.Argument(..., help="Natural language intent to dispatch"),
    payload: str = typer.Option("{}", "--payload", "-p", help="JSON payload string"),
    no_wait: bool = typer.Option(False, "--no-wait", help="Return immediately with the pending task id"),
) -> None:
    """Dispatch a task through the agency."""
    engine = AgencyEngine(_load_config())
    data: dict[str, Any] = json.loads(payload)

    async def _run() -> None:
        await engine.start_worker()
        try:
            task = await engine.dispatch(intent, data)
            if no_wait:
                console.print(Panel(
                    f"Task [bold cyan]{task.id}[/bold cyan] dispatched\n"
                    f"Status: [bold]{task.status.value}[/bold]",
                    title="Dispatched",
                    border_style="yellow",
                ))
                return

            with console.status(f"[bold yellow]Executing: {intent}"):
                for _ in range(240):  # 2 minute max wait
                    current = engine.get_task(task.id)
                    if current.status.value in ("completed", "failed", "cancelled"):
                        break
                    await asyncio.sleep(0.5)

            final = engine.get_task(task.id)
            if final.module_id:
                console.print(Panel(
                    f"Routed to [bold cyan]{final.module_id}[/bold cyan] ([italic]{final.category.value}[/italic])\n"
                    f"Status: [bold]{final.status.value}[/bold]\n"
                    f"Result: {json.dumps(final.result, indent=2, default=str)}",
                    title=f"Task {final.id}",
                    border_style="green" if final.status.value == "completed" else "red",
                ))
            else:
                console.print(Panel(
                    f"No module matched. Category: {final.category.value}\n"
                    f"Status: [bold]{final.status.value}[/bold]\n"
                    f"Result: {json.dumps(final.result, indent=2, default=str)}",
                    title=f"Task {final.id}",
                    border_style="yellow",
                ))
        finally:
            await engine.stop_worker()

    asyncio.run(_run())
```

Add the `task status` command after the `dispatch` command:

```python
@task_app.command("status")
def task_status(
    task_id: str = typer.Argument(..., help="Task id to look up"),
) -> None:
    """Show the current status of a dispatched task."""
    engine = AgencyEngine(_load_config())

    async def _run() -> None:
        await engine.start_worker()
        try:
            task = engine.get_task(task_id)
            if task is None:
                console.print(f"[red]Task '{task_id}' not found.[/red]")
                raise typer.Exit(1)

            result_preview = ""
            if task.result:
                result_preview = json.dumps(task.result, indent=2, default=str)[:2000]
            error_preview = task.error or ""

            console.print(Panel(
                f"Status: [bold]{task.status.value}[/bold]\n"
                f"Created: {task.created_at}\n"
                f"Started: {task.started_at or 'N/A'}\n"
                f"Completed: {task.completed_at or 'N/A'}\n"
                f"Module: {task.module_id or 'N/A'}\n"
                f"Category: {task.category.value if task.category else 'N/A'}\n"
                f"\n[bold]Result:[/bold]\n{result_preview}\n"
                f"[bold]Error:[/bold]\n{error_preview}",
                title=f"Task {task.id}",
                border_style="green" if task.status.value == "completed" else "red" if task.status.value == "failed" else "yellow",
            ))
        finally:
            await engine.stop_worker()

    asyncio.run(_run())
```

- [ ] **Step 4: Run CLI tests**

Run:
```bash
source .venv/Scripts/activate
python -m pytest tests/test_cli.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sahiixx_agency/cli/main.py tests/test_cli.py
git commit -m "feat(cli): poll dispatch output and add opa task status"
```

---

### Task 5: Full verification

**Files:**
- All modified files.

- [ ] **Step 1: Run the full Python test suite**

Run:
```bash
source .venv/Scripts/activate
python -m pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 2: Run the linter**

Run:
```bash
source .venv/Scripts/activate
ruff check sahiixx_agency tests
ruff format --check sahiixx_agency tests
```

Expected: No lint errors; formatting check passes. If formatting check fails, run `ruff format sahiixx_agency tests` and commit the result.

- [ ] **Step 3: Run type check (optional but recommended)**

Run:
```bash
source .venv/Scripts/activate
mypy sahiixx_agency
```

Expected: No new type errors introduced. Pre-existing errors may remain.

- [ ] **Step 4: Commit any formatting fixes**

```bash
git add -A
git commit -m "style: apply ruff formatting" || echo "nothing to commit"
```

---

## Self-review checklist for the plan

1. **Spec coverage:**
   - Worker queue + non-blocking dispatch → Task 1.
   - Task status lookup (`get_task`, `list_tasks`) → Tasks 1 & 2.
   - `GET /tasks/{task_id}` + lifespan wiring → Task 3.
   - CLI polling + `opa task status` → Task 4.
   - Tests for all surfaces → Tasks 2, 3, 4, 5.

2. **Placeholder scan:** No TBD/TODO/similar placeholders.

3. **Type consistency:**
   - `start_worker()` / `stop_worker()` are async across engine, API, CLI.
   - `get_task(task_id: str) -> AgencyTask | None` is used consistently.
   - `TaskStatus.PENDING` is introduced in router and checked in tests.
