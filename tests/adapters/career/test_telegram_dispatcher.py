"""Tests for the Career-Ops Telegram dispatcher."""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sahiixx_agency.adapters.career.telegram_dispatcher import (
    CareerOpsDispatcher,
    CareerOpsTelegramBot,
    DispatchResult,
    run_bot,
)


def test_extract_url_finds_first_url() -> None:
    assert CareerOpsDispatcher.extract_url("Check https://example.com/jobs/1 here") == "https://example.com/jobs/1"


def test_extract_url_returns_none_when_missing() -> None:
    assert CareerOpsDispatcher.extract_url("no url here") is None


def test_dispatch_uses_custom_command_builder() -> None:
    def builder(url: str, use_claude: bool = False) -> list[str]:
        return ["echo", url]

    dispatcher = CareerOpsDispatcher(command_builder=builder)
    result = dispatcher.dispatch("https://example.com")
    assert result.ok is True
    assert "https://example.com" in result.stdout


def test_dispatch_handles_timeout() -> None:
    def builder(url: str, use_claude: bool = False) -> list[str]:
        return ["sleep", "10"]

    dispatcher = CareerOpsDispatcher(command_builder=builder, timeout=0.1)
    result = dispatcher.dispatch("https://example.com")
    assert result.ok is False
    assert result.returncode == -1


def test_dispatch_handles_subprocess_error() -> None:
    def builder(url: str, use_claude: bool = False) -> list[str]:
        return ["false"]

    dispatcher = CareerOpsDispatcher(command_builder=builder)
    result = dispatcher.dispatch("https://example.com")
    assert result.ok is False
    assert result.returncode == 1


def test_dispatch_handles_exception() -> None:
    def builder(url: str, use_claude: bool = False) -> list[str]:
        raise RuntimeError("boom")

    dispatcher = CareerOpsDispatcher(command_builder=builder)
    result = dispatcher.dispatch("https://example.com")
    assert result.ok is False
    assert "boom" in result.stderr


def test_format_reply_success() -> None:
    result = DispatchResult(ok=True, stdout="hello", stderr="", command="echo hello", returncode=0)
    reply = CareerOpsDispatcher.format_reply(result)
    assert "✅ Done" in reply
    assert "hello" in reply


def test_format_reply_failure() -> None:
    result = DispatchResult(ok=False, stdout="", stderr="oops", command="false", returncode=1)
    reply = CareerOpsDispatcher.format_reply(result)
    assert "❌ Failed" in reply
    assert "oops" in reply


async def _capture_handlers(bot: CareerOpsTelegramBot) -> dict[str, Any]:
    """Build the app via the bot and return the registered handler callbacks."""
    handlers: dict[str, Any] = {}
    app = MagicMock()

    def capture_add_handler(handler) -> None:
        handlers[handler.callback.__name__] = handler.callback

    app.add_handler.side_effect = capture_add_handler
    app.run_polling = lambda: asyncio.sleep(3600)

    with patch.object(bot, "_build_app", return_value=app):
        run_task = asyncio.create_task(bot.run())
        await asyncio.sleep(0)
        run_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await run_task

    return handlers


@pytest.mark.asyncio
async def test_handle_message_dispatches_url() -> None:
    update = MagicMock()
    update.effective_message.text = "Apply here https://jobs.example.com/123"
    update.effective_message.reply_text = AsyncMock()

    context = MagicMock()
    context.bot_data = {"dry_run": False, "dispatcher": CareerOpsDispatcher(command_builder=lambda url, _: ["echo", f"ran {url}"])}

    bot = CareerOpsTelegramBot(token="dummy")
    handlers = await _capture_handlers(bot)
    handle_message = handlers["handle_message"]
    await handle_message(update, context)

    reply = update.effective_message.reply_text.call_args_list[-1][0][0]
    assert "ran https://jobs.example.com/123" in reply


@pytest.mark.asyncio
async def test_handle_message_dry_run() -> None:
    update = MagicMock()
    update.effective_message.text = "https://jobs.example.com/456"
    update.effective_message.reply_text = AsyncMock()

    context = MagicMock()
    context.bot_data = {"dry_run": True}

    bot = CareerOpsTelegramBot(token="dummy")
    handlers = await _capture_handlers(bot)
    handle_message = handlers["handle_message"]
    await handle_message(update, context)

    reply = update.effective_message.reply_text.call_args_list[-1][0][0]
    assert "[DRY RUN]" in reply


def test_run_bot_requires_token(monkeypatch) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="Telegram bot token is required"):
        run_bot(token=None, dry_run=True)


def test_run_bot_uses_env_token(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")

    def fake_run(self) -> None:
        return None

    with patch.object(CareerOpsTelegramBot, "run_sync", fake_run):
        # Should not raise
        run_bot(dry_run=True)
