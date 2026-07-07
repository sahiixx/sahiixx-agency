"""Tests for the structured task logger and API endpoint."""

from __future__ import annotations

import json
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from sahiixx_agency.api.main import app, get_engine
from sahiixx_agency.core.engine import AgencyEngine
from sahiixx_agency.core.logger import TaskLogger
from sahiixx_agency.core.models import AgencyConfig, AgencyTask, RepoCategory, RepoNode, RiskLevel, TaskStatus


@pytest.fixture
def logger(tmp_path):
    return TaskLogger(str(tmp_path))


@pytest.mark.asyncio
async def test_log_creates_jsonl_file(logger, tmp_path):
    await logger.info("task_1", "hello", actor="engine", module_id="mod")
    path = tmp_path / "task-logs" / "task_1.jsonl"
    assert path.exists()
    lines = path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["task_id"] == "task_1"
    assert entry["level"] == "INFO"
    assert entry["actor"] == "engine"
    assert entry["message"] == "hello"
    assert entry["extra"] == {"module_id": "mod"}
    assert "timestamp" in entry


@pytest.mark.asyncio
async def test_log_levels(logger, tmp_path):
    await logger.debug("task_2", "debug msg")
    await logger.info("task_2", "info msg")
    await logger.warning("task_2", "warning msg")
    await logger.error("task_2", "error msg")

    entries = await logger.read("task_2")
    assert [e["level"] for e in entries] == ["DEBUG", "INFO", "WARNING", "ERROR"]


@pytest.mark.asyncio
async def test_read_returns_empty_list_for_missing_task(logger):
    assert await logger.read("task_missing") == []


@pytest.mark.asyncio
async def test_read_ignores_blank_lines(logger, tmp_path):
    await logger.info("task_3", "first")
    path = tmp_path / "task-logs" / "task_3.jsonl"
    path.write_text(path.read_text(encoding="utf-8") + "\n\n", encoding="utf-8")
    entries = await logger.read("task_3")
    assert len(entries) == 1


@pytest.mark.asyncio
async def test_log_returns_entry(logger):
    entry = await logger.log("task_4", "WARNING", "watch out", actor="approval", reason="risky")
    assert entry["level"] == "WARNING"
    assert entry["actor"] == "approval"
    assert entry["extra"] == {"reason": "risky"}


@pytest.mark.asyncio
async def test_read_skips_corrupt_json_lines(logger, tmp_path):
    await logger.info("task_corrupt", "valid entry")
    path = tmp_path / "task-logs" / "task_corrupt.jsonl"
    with open(path, "a", encoding="utf-8") as f:
        f.write("this is not json\n")
        f.write('{"level": "INFO", "task_id": "task_corrupt", "message": "second"}\n')
        f.write("[broken\n")

    entries = await logger.read("task_corrupt")
    assert len(entries) == 2
    assert entries[0]["message"] == "valid entry"
    assert entries[1]["message"] == "second"


@pytest.mark.asyncio
async def test_log_handles_non_serializable_extra(logger, tmp_path):
    now = datetime.now(timezone.utc)
    entry = await logger.info(
        "task_extra",
        "with datetime",
        actor="engine",
        created_at=now,
        raw_object=object(),
    )
    assert entry["extra"]["created_at"] == now.isoformat()
    assert isinstance(entry["extra"]["raw_object"], str)

    entries = await logger.read("task_extra")
    assert len(entries) == 1
    assert entries[0]["extra"]["created_at"] == now.isoformat()


@pytest.mark.asyncio
async def test_engine_logs_dispatch(tmp_path):
    config = AgencyConfig(data_dir=str(tmp_path))
    engine = AgencyEngine(config)
    module = RepoNode(
        id="echo",
        name="echo",
        full_name="test/echo",
        url="https://github.com/test/echo",
        category=RepoCategory.AGENT_FRAMEWORK,
    )
    engine.registry._modules["echo"] = module

    task = await engine.dispatch("run echo", {})
    logs = await engine.task_logger.read(task.id)
    assert any(e["message"] == "Task dispatched" for e in logs)
    dispatch = next(e for e in logs if e["message"] == "Task dispatched")
    assert dispatch["actor"] == "engine"
    assert dispatch["level"] == "INFO"
    assert dispatch["extra"]["intent"] == "run echo"


@pytest.mark.asyncio
async def test_engine_logs_task_lifecycle(tmp_path, monkeypatch):
    config = AgencyConfig(data_dir=str(tmp_path))
    engine = AgencyEngine(config)
    module = RepoNode(
        id="echo",
        name="echo",
        full_name="test/echo",
        url="https://github.com/test/echo",
        category=RepoCategory.AGENT_FRAMEWORK,
    )
    engine.registry._modules["echo"] = module

    async def fake_run(mod, command="run", env=None, timeout=60):
        return {"status": "success", "returncode": 0, "stdout": "ok"}

    monkeypatch.setattr(engine.runner, "run", fake_run)

    task = AgencyTask(id="task_lifecycle", intent="run echo", module_id="echo")
    engine._tasks[task.id] = task
    await engine._execute_task(task)

    assert task.status == TaskStatus.COMPLETED
    logs = await engine.task_logger.read(task.id)
    messages = [e["message"] for e in logs]
    assert "Task execution started" in messages
    assert "Task completed" in messages


@pytest.mark.asyncio
async def test_engine_logs_task_failure(tmp_path, monkeypatch):
    config = AgencyConfig(data_dir=str(tmp_path))
    engine = AgencyEngine(config)
    module = RepoNode(
        id="broken",
        name="broken",
        full_name="test/broken",
        url="https://github.com/test/broken",
        category=RepoCategory.AGENT_FRAMEWORK,
    )
    engine.registry._modules["broken"] = module

    async def fake_run(self, mod, payload):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "sahiixx_agency.adapters.generic_adapter.GenericAdapter.run",
        fake_run,
    )

    task = AgencyTask(id="task_fail", intent="run broken", module_id="broken")
    engine._tasks[task.id] = task
    await engine._execute_task(task)

    assert task.status == TaskStatus.FAILED
    logs = await engine.task_logger.read(task.id)
    error_logs = [e for e in logs if e["message"] == "Task failed"]
    assert len(error_logs) == 1
    assert error_logs[0]["level"] == "ERROR"
    assert "boom" in error_logs[0]["extra"]["error"]


@pytest.mark.asyncio
async def test_engine_logs_approval_requested(tmp_path):
    config = AgencyConfig(data_dir=str(tmp_path))
    engine = AgencyEngine(config)
    module = RepoNode(
        id="danger",
        name="danger",
        full_name="test/danger",
        url="https://github.com/test/danger",
        category=RepoCategory.SECURITY,
        risk_level=RiskLevel.HIGH,
    )
    engine.registry._modules["danger"] = module

    task = AgencyTask(id="task_approval", intent="run danger", module_id="danger")
    engine._tasks[task.id] = task
    await engine._execute_task(task)

    assert task.status == TaskStatus.PENDING
    logs = await engine.task_logger.read(task.id)
    req_logs = [e for e in logs if e["message"] == "Approval requested"]
    assert len(req_logs) == 1
    assert req_logs[0]["actor"] == "approval"
    assert req_logs[0]["extra"]["risk_level"] == "high"


@pytest.mark.asyncio
async def test_engine_logs_approval_approved(tmp_path):
    config = AgencyConfig(data_dir=str(tmp_path))
    engine = AgencyEngine(config)
    task = AgencyTask(id="task_approve", intent="run danger")
    engine._tasks[task.id] = task
    engine.approval_manager.request_approval(task, RiskLevel.HIGH, "risky")

    await engine.approve_task(task.id, by="tester")
    logs = await engine.task_logger.read(task.id)
    assert any(e["message"] == "Approval granted" and e["actor"] == "approval" for e in logs)


@pytest.mark.asyncio
async def test_engine_logs_approval_rejected(tmp_path):
    config = AgencyConfig(data_dir=str(tmp_path))
    engine = AgencyEngine(config)
    task = AgencyTask(id="task_reject", intent="run danger")
    engine._tasks[task.id] = task
    engine.approval_manager.request_approval(task, RiskLevel.HIGH, "risky")

    await engine.reject_task(task.id, by="tester")
    logs = await engine.task_logger.read(task.id)
    assert any(e["message"] == "Approval rejected" and e["actor"] == "approval" for e in logs)


@pytest.mark.asyncio
async def test_engine_logs_chat_dispatch(tmp_path, monkeypatch):
    config = AgencyConfig(data_dir=str(tmp_path))
    engine = AgencyEngine(config)
    module = RepoNode(
        id="echo",
        name="echo",
        full_name="test/echo",
        url="https://github.com/test/echo",
        category=RepoCategory.AGENT_FRAMEWORK,
    )
    engine.registry._modules["echo"] = module

    async def fake_run(mod, command="run", env=None, timeout=60):
        return {"status": "success", "returncode": 0, "stdout": "ok"}

    monkeypatch.setattr(engine.runner, "run", fake_run)

    thread, message, task = await engine.chat_message(None, "run echo")
    logs = await engine.task_logger.read(task.id)
    assert any(e["message"] == "Chat message dispatched as task" and e["actor"] == "chat" for e in logs)


@pytest.mark.asyncio
async def test_task_log_entry_model(logger):
    from sahiixx_agency.core.models import TaskLogEntry

    entry = await logger.info("task_model", "msg", actor="api", custom="value")
    validated = TaskLogEntry.model_validate(entry)
    assert validated.task_id == "task_model"
    assert validated.actor == "api"
    assert validated.extra["custom"] == "value"


@pytest.mark.asyncio
async def test_engine_logs_dependency_scan_failure(tmp_path, monkeypatch):
    config = AgencyConfig(data_dir=str(tmp_path))
    config.security.dependency_scan_enabled = True
    engine = AgencyEngine(config)
    module = RepoNode(
        id="vulnerable",
        name="vulnerable",
        full_name="test/vulnerable",
        url="https://github.com/test/vulnerable",
        category=RepoCategory.AGENT_FRAMEWORK,
    )
    engine.registry._modules["vulnerable"] = module

    class FakeReport:
        passed = False
        failures = ["CVE-123"]
        command = "safety check"
        stderr = ""

        def model_dump(self, mode="json"):
            return {"passed": False, "failures": self.failures, "command": self.command, "stderr": self.stderr}

    async def fake_scan(mod):
        return FakeReport()

    monkeypatch.setattr(engine.dependency_scanner, "scan", fake_scan)

    task = AgencyTask(id="task_scan", intent="run vulnerable", module_id="vulnerable")
    engine._tasks[task.id] = task
    await engine._execute_task(task)

    assert task.status == TaskStatus.FAILED
    logs = await engine.task_logger.read(task.id)
    scan_logs = [e for e in logs if e["message"] == "Dependency vulnerability scan failed"]
    assert len(scan_logs) == 1
    assert scan_logs[0]["level"] == "ERROR"
    assert "CVE-123" in scan_logs[0]["extra"]["failures"]


@pytest.mark.asyncio
async def test_log_dir_created_lazily(logger, tmp_path):
    path = tmp_path / "task-logs"
    assert not path.exists()
    await logger.info("task_lazy", "first")
    assert path.exists()


@pytest.mark.asyncio
async def test_log_appends_to_existing_file(logger, tmp_path):
    await logger.info("task_append", "one")
    await logger.info("task_append", "two")
    entries = await logger.read("task_append")
    assert len(entries) == 2
    assert entries[0]["message"] == "one"
    assert entries[1]["message"] == "two"


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    config = AgencyConfig(data_dir=str(tmp_path))
    engine = AgencyEngine(config)

    module = RepoNode(
        id="echo-module",
        name="echo-module",
        full_name="sahiixx/echo-module",
        url="https://github.com/sahiixx/echo-module",
        category=RepoCategory.AGENT_FRAMEWORK,
        language="python",
        stars=10,
        capabilities=["echo"],
    )
    engine.registry._modules["echo-module"] = module

    async def fake_run(mod, command="run", env=None, timeout=60):
        return {"module": mod.name, "status": "success", "returncode": 0, "stdout": "ok", "stderr": "", "command": command}

    monkeypatch.setattr(engine.runner, "run", fake_run)

    @asynccontextmanager
    async def _noop_lifespan(_app):
        yield

    app.dependency_overrides[get_engine] = lambda: engine
    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = _noop_lifespan
    try:
        with TestClient(app) as test_client:
            test_client.portal.call(engine.start_worker)
            yield test_client
            test_client.portal.call(engine.stop_worker)
    finally:
        app.dependency_overrides.clear()
        app.router.lifespan_context = original_lifespan


def test_get_task_logs_endpoint(api_client):
    create = api_client.post("/tasks", params={"intent": "run echo assistant"})
    assert create.status_code == 200
    task_id = create.json()["id"]

    # Wait for the worker to process the task.
    status = "pending"
    for _ in range(20):
        resp = api_client.get(f"/tasks/{task_id}")
        status = resp.json()["status"]
        if status in ("completed", "failed"):
            break
        time.sleep(0.05)
    assert status == "completed"

    response = api_client.get(f"/tasks/{task_id}/logs")
    assert response.status_code == 200
    logs = response.json()
    assert isinstance(logs, list)
    assert any(e["message"] == "Task dispatched" for e in logs)
    assert any(e["message"] == "Task execution started" for e in logs)
    assert any(e["message"] == "Task completed" for e in logs)
    assert all("timestamp" in e and "level" in e and "actor" in e for e in logs)


def test_get_task_logs_empty_for_unknown_task(api_client):
    response = api_client.get("/tasks/task_does_not_exist/logs")
    assert response.status_code == 200
    assert response.json() == []
