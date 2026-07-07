"""Tests for the general agency Telegram bot."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sahiixx_agency.core.engine import AgencyEngine
from sahiixx_agency.core.models import (
    AgencyConfig,
    AgencyTask,
    RepoCategory,
    RepoNode,
    RiskLevel,
    TaskStatus,
    TelegramConfig,
)
from sahiixx_agency.telegram.bot import AgencyTelegramBot, TelegramAuthorizationError, run_bot


@pytest.fixture
def engine(tmp_path, monkeypatch):
    config = AgencyConfig(
        data_dir=str(tmp_path),
        telegram=TelegramConfig(allowed_chat_ids=[12345]),
    )
    eng = AgencyEngine(config)

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
    eng.registry._modules[module.id] = module

    async def fake_discover(username):
        return [module]

    async def fake_generic_run(self, node, payload):
        return {"status": "success", "module": node.name}

    monkeypatch.setattr(eng.registry, "discover", fake_discover)
    monkeypatch.setattr("sahiixx_agency.adapters.generic_adapter.GenericAdapter.run", fake_generic_run)
    return eng


@pytest.fixture
def bot(engine):
    return AgencyTelegramBot(
        token="dummy",
        engine=engine,
        config=engine.config,
        poll_interval=0.05,
        max_poll_seconds=2.0,
    )


def _make_update(text: str = "", chat_id: int = 12345) -> MagicMock:
    update = MagicMock()
    update.effective_chat.id = chat_id
    update.effective_message.text = text
    update.effective_message.reply_text = AsyncMock()
    return update


def _make_callback_update(data: str, chat_id: int = 12345) -> MagicMock:
    update = MagicMock()
    update.effective_chat.id = chat_id
    update.effective_message.reply_text = AsyncMock()
    update.callback_query = MagicMock()
    update.callback_query.data = data
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    return update


@pytest.mark.asyncio
async def test_start_command(bot):
    update = _make_update("/start")
    await bot._cmd_start(update, None)
    reply = update.effective_message.reply_text.call_args[0][0]
    assert "One Person Agency Bot" in reply


@pytest.mark.asyncio
async def test_unauthorized_chat(bot):
    update = _make_update("/start", chat_id=99999)
    await bot._cmd_start(update, None)
    reply = update.effective_message.reply_text.call_args[0][0]
    assert "not authorized" in reply


@pytest.mark.asyncio
async def test_dispatch_command(bot):
    await bot.engine.start_worker()
    try:
        update = _make_update("/dispatch run echo hello")
        await bot._cmd_dispatch(update, None)

        replies = [call[0][0] for call in update.effective_message.reply_text.call_args_list]
        assert any("Dispatching" in r for r in replies)
        assert any("echo-module" in r or "completed" in r for r in replies)
    finally:
        await bot.engine.stop_worker()


@pytest.mark.asyncio
async def test_dispatch_command_without_intent(bot):
    update = _make_update("/dispatch")
    await bot._cmd_dispatch(update, None)
    reply = update.effective_message.reply_text.call_args[0][0]
    assert "Usage" in reply


@pytest.mark.asyncio
async def test_text_message_dispatch(bot):
    await bot.engine.start_worker()
    try:
        update = _make_update("run echo hello")
        await bot._handle_text(update, None)

        replies = [call[0][0] for call in update.effective_message.reply_text.call_args_list]
        assert any("Dispatching" in r for r in replies)
        assert any("echo-module" in r or "completed" in r for r in replies)
    finally:
        await bot.engine.stop_worker()


@pytest.mark.asyncio
async def test_tasks_command(bot):
    bot.engine._tasks["task_a"] = AgencyTask(id="task_a", intent="scan", status=TaskStatus.COMPLETED)
    update = _make_update("/tasks")
    await bot._cmd_tasks(update, None)
    reply = update.effective_message.reply_text.call_args[0][0]
    assert "task_a" in reply


@pytest.mark.asyncio
async def test_task_command(bot):
    bot.engine._tasks["task_b"] = AgencyTask(
        id="task_b",
        intent="scan",
        status=TaskStatus.COMPLETED,
        module_id="echo-module",
    )
    update = _make_update("/task task_b")
    await bot._cmd_task(update, None)
    reply = update.effective_message.reply_text.call_args[0][0]
    assert "task_b" in reply
    assert "completed" in reply


@pytest.mark.asyncio
async def test_task_command_not_found(bot):
    update = _make_update("/task missing")
    await bot._cmd_task(update, None)
    reply = update.effective_message.reply_text.call_args[0][0]
    assert "not found" in reply


@pytest.mark.asyncio
async def test_approve_command(bot):
    await bot.engine.start_worker()
    try:
        task = AgencyTask(id="task_risk", intent="dangerous scan", module_id="echo-module")
        bot.engine._tasks[task.id] = task
        bot.engine.approval_manager.request_approval(task, RiskLevel.HIGH, "risky")

        update = _make_update(f"/approve {task.id}")
        await bot._cmd_approve(update, None)

        replies = [call[0][0] for call in update.effective_message.reply_text.call_args_list]
        assert any("Approved" in r for r in replies)
        assert bot.engine.approval_manager.is_approved(task.id)
    finally:
        await bot.engine.stop_worker()


@pytest.mark.asyncio
async def test_reject_command(bot):
    task = AgencyTask(id="task_risk", intent="dangerous scan", module_id="echo-module")
    bot.engine._tasks[task.id] = task
    bot.engine.approval_manager.request_approval(task, RiskLevel.HIGH, "risky")

    update = _make_update(f"/reject {task.id}")
    await bot._cmd_reject(update, None)

    reply = update.effective_message.reply_text.call_args[0][0]
    assert "Rejected" in reply
    assert bot.engine.approval_manager.is_rejected(task.id)


@pytest.mark.asyncio
async def test_approvals_command(bot):
    task = AgencyTask(id="task_pending", intent="dangerous scan", module_id="echo-module")
    bot.engine._tasks[task.id] = task
    bot.engine.approval_manager.request_approval(task, RiskLevel.HIGH, "risky")

    update = _make_update("/approvals")
    await bot._cmd_approvals(update, None)
    reply = update.effective_message.reply_text.call_args[0][0]
    assert "task_pending" in reply


@pytest.mark.asyncio
async def test_stats_command(bot):
    update = _make_update("/stats")
    await bot._cmd_stats(update, None)
    reply = update.effective_message.reply_text.call_args[0][0]
    assert "Agency Stats" in reply


@pytest.mark.asyncio
async def test_registry_command(bot):
    update = _make_update("/registry")
    await bot._cmd_registry(update, None)
    reply = update.effective_message.reply_text.call_args[0][0]
    assert "echo-module" in reply


@pytest.mark.asyncio
async def test_callback_approve(bot):
    await bot.engine.start_worker()
    try:
        task = AgencyTask(id="task_cb", intent="dangerous scan", module_id="echo-module")
        bot.engine._tasks[task.id] = task
        bot.engine.approval_manager.request_approval(task, RiskLevel.HIGH, "risky")

        update = _make_callback_update(f"approve:{task.id}")
        await bot._callback_approve(update, None)

        edit_text = update.callback_query.edit_message_text.call_args[0][0]
        assert "Approved" in edit_text
        assert bot.engine.approval_manager.is_approved(task.id)
    finally:
        await bot.engine.stop_worker()


@pytest.mark.asyncio
async def test_callback_reject(bot):
    task = AgencyTask(id="task_cb", intent="dangerous scan", module_id="echo-module")
    bot.engine._tasks[task.id] = task
    bot.engine.approval_manager.request_approval(task, RiskLevel.HIGH, "risky")

    update = _make_callback_update(f"reject:{task.id}")
    await bot._callback_reject(update, None)

    edit_text = update.callback_query.edit_message_text.call_args[0][0]
    assert "Rejected" in edit_text
    assert bot.engine.approval_manager.is_rejected(task.id)


@pytest.mark.asyncio
async def test_high_risk_task_sends_approval_request(bot):
    bot.engine.registry._modules["echo-module"].risk_level = RiskLevel.CRITICAL
    update = _make_update("run echo hello")
    await bot._handle_text(update, None)

    replies = [call[0][0] for call in update.effective_message.reply_text.call_args_list]
    assert any("Approval required" in r for r in replies)


def test_run_bot_requires_token(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="Telegram bot token is required"):
        run_bot(token=None)


def test_run_bot_uses_env_token(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")

    async def fake_run(self):
        return None

    with patch.object(AgencyTelegramBot, "run", fake_run):
        # Should not raise
        run_bot()


def test_authorization_error_carries_chat_id():
    err = TelegramAuthorizationError(12345)
    assert err.args[0] == 12345
