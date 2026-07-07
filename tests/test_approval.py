"""Tests for the approval gate."""

from __future__ import annotations

import pytest

from sahiixx_agency.core.approval import ApprovalManager
from sahiixx_agency.core.engine import AgencyEngine
from sahiixx_agency.core.models import AgencyConfig, AgencyTask, RepoCategory, RepoNode, RiskLevel, TaskStatus


def test_approval_required_for_high_risk() -> None:
    mgr = ApprovalManager()
    task = AgencyTask(id="task_1", intent="scan target", module_id="t3mp3st", payload={"risk_level": "critical"})
    req = mgr.request_approval(task, RiskLevel.CRITICAL, "security tool")
    assert req.status == "pending"
    assert not mgr.is_approved("task_1")
    mgr.approve(req.id, by="user")
    assert mgr.is_approved("task_1")


def test_approval_reject_marks_task_rejected() -> None:
    mgr = ApprovalManager()
    task = AgencyTask(id="task_2", intent="scan target", module_id="t3mp3st")
    req = mgr.request_approval(task, RiskLevel.HIGH, "security tool")
    mgr.reject(req.id, by="user")
    assert mgr.is_rejected("task_2")
    assert not mgr.is_approved("task_2")


def test_approve_by_task() -> None:
    mgr = ApprovalManager()
    task = AgencyTask(id="task_3", intent="scan target", module_id="t3mp3st")
    mgr.request_approval(task, RiskLevel.HIGH, "security tool")
    approved = mgr.approve_by_task("task_3", by="user")
    assert approved is not None
    assert approved.status == "approved"
    assert mgr.is_approved("task_3")


def test_list_pending() -> None:
    mgr = ApprovalManager()
    task = AgencyTask(id="task_4", intent="scan target", module_id="t3mp3st")
    mgr.request_approval(task, RiskLevel.CRITICAL, "security tool")
    pending = mgr.list_pending()
    assert len(pending) == 1
    assert pending[0].task_id == "task_4"


def test_unknown_task_not_approved() -> None:
    mgr = ApprovalManager()
    assert not mgr.is_approved("unknown")


@pytest.mark.asyncio
async def test_engine_blocks_high_risk_task_until_approved(tmp_path) -> None:
    config = AgencyConfig(data_dir=str(tmp_path))
    engine = AgencyEngine(config)

    module = RepoNode(
        id="danger-module",
        name="danger-module",
        full_name="test/danger-module",
        url="https://github.com/test/danger-module",
        category=RepoCategory.SECURITY,
        risk_level=RiskLevel.HIGH,
    )
    engine.registry._modules["danger-module"] = module

    task = AgencyTask(
        id="task_high_risk",
        intent="run dangerous scan",
        module_id="danger-module",
        payload={},
    )
    engine._tasks[task.id] = task
    await engine._execute_task(task)

    assert task.status == TaskStatus.PENDING
    assert not engine.approval_manager.is_approved("task_high_risk")
    assert len(engine.approval_manager.list_pending()) == 1

    await engine.approve_task("task_high_risk", by="user")
    # Task is now approved; a subsequent execution attempt would run.
    assert engine.approval_manager.is_approved("task_high_risk")


@pytest.mark.asyncio
async def test_engine_uses_payload_risk_level(tmp_path) -> None:
    config = AgencyConfig(data_dir=str(tmp_path))
    engine = AgencyEngine(config)

    task = AgencyTask(
        id="task_payload_risk",
        intent="run scan",
        module_id="safe-module",
        payload={"risk_level": "critical"},
    )
    engine._tasks[task.id] = task
    await engine._execute_task(task)

    assert task.status == TaskStatus.PENDING
    assert engine.approval_manager.list_pending()[0].risk_level == RiskLevel.CRITICAL
