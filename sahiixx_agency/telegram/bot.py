"""Telegram bot for general agency tasks and approvals.

The bot exposes the agency engine through a chat interface:
- Dispatch natural-language tasks
- List and inspect tasks
- Approve or reject high-risk tasks
- View registry and stats
"""

from __future__ import annotations

import asyncio
import html
import os
from typing import Any

from sahiixx_agency.core.engine import AgencyEngine
from sahiixx_agency.core.models import AgencyConfig, AgencyTask, RiskLevel, TaskStatus


class TelegramAuthorizationError(Exception):
    """Raised when a chat ID is not authorized to use the bot."""


class AgencyTelegramBot:
    """Telegram bot that proxies agency tasks and approvals."""

    def __init__(
        self,
        token: str,
        engine: AgencyEngine | None = None,
        config: AgencyConfig | None = None,
        poll_interval: float = 0.5,
        max_poll_seconds: float = 120.0,
    ) -> None:
        self.token = token
        self.config = config or AgencyConfig()
        self.engine = engine or AgencyEngine(self.config)
        self.poll_interval = poll_interval
        self.max_poll_seconds = max_poll_seconds

    def _is_authorized(self, chat_id: int) -> bool:
        allowed = self.config.telegram.allowed_chat_ids
        return not allowed or chat_id in allowed

    def _check_auth(self, update: Any) -> int:
        chat_id = int(update.effective_chat.id)
        if not self._is_authorized(chat_id):
            raise TelegramAuthorizationError(chat_id)
        return chat_id

    def _build_app(self) -> Any:
        from telegram.ext import ApplicationBuilder

        return ApplicationBuilder().token(self.token).build()

    async def setup_engine(self) -> None:
        """Start the agency worker and optionally sync the registry."""
        await self.engine.start_worker()
        if not self.engine.registry.modules:
            await self.engine.sync_repos(self.engine.config.github_username)

    async def shutdown_engine(self) -> None:
        await self.engine.stop_worker()

    async def run(self) -> None:
        """Run the bot with long polling."""
        from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler, filters

        await self.setup_engine()
        application = self._build_app()
        application.bot_data["bot"] = self

        application.add_handler(CommandHandler("start", self._cmd_start))
        application.add_handler(CommandHandler("help", self._cmd_help))
        application.add_handler(CommandHandler("dispatch", self._cmd_dispatch))
        application.add_handler(CommandHandler("tasks", self._cmd_tasks))
        application.add_handler(CommandHandler("task", self._cmd_task))
        application.add_handler(CommandHandler("approve", self._cmd_approve))
        application.add_handler(CommandHandler("reject", self._cmd_reject))
        application.add_handler(CommandHandler("approvals", self._cmd_approvals))
        application.add_handler(CommandHandler("stats", self._cmd_stats))
        application.add_handler(CommandHandler("registry", self._cmd_registry))
        application.add_handler(CallbackQueryHandler(self._callback_approve, pattern=r"^approve:"))
        application.add_handler(CallbackQueryHandler(self._callback_reject, pattern=r"^reject:"))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text))

        try:
            await application.run_polling(poll_interval=1, timeout=self.config.telegram.poll_timeout)
        finally:
            await self.shutdown_engine()

    async def _cmd_start(self, update: Any, _context: Any) -> None:
        try:
            self._check_auth(update)
        except TelegramAuthorizationError:
            await self._reply(update, "⛔ You are not authorized to use this bot.")
            return
        await self._reply(
            update,
            "👋 <b>One Person Agency Bot</b>\n\n"
            "Send me a natural-language task or use /help to see commands.",
        )

    async def _cmd_help(self, update: Any, _context: Any) -> None:
        try:
            self._check_auth(update)
        except TelegramAuthorizationError:
            await self._reply(update, "⛔ You are not authorized to use this bot.")
            return
        await self._reply(
            update,
            "<b>Available commands</b>\n\n"
            "/dispatch &lt;intent&gt; — Dispatch a task\n"
            "/tasks — List recent tasks\n"
            "/task &lt;id&gt; — Show task status\n"
            "/approve &lt;id&gt; — Approve a risky task\n"
            "/reject &lt;id&gt; — Reject a risky task\n"
            "/approvals — List pending approvals\n"
            "/stats — Agency statistics\n"
            "/registry — List modules\n\n"
            "You can also simply type a task and I will dispatch it.",
        )

    async def _cmd_dispatch(self, update: Any, _context: Any) -> None:
        try:
            self._check_auth(update)
        except TelegramAuthorizationError:
            await self._reply(update, "⛔ You are not authorized to use this bot.")
            return
        text = update.effective_message.text or ""
        intent = text.split(" ", 1)[1] if len(text.split(" ", 1)) > 1 else ""
        if not intent.strip():
            await self._reply(update, "Usage: /dispatch &lt;intent&gt;")
            return
        await self._dispatch_intent(update, intent)

    async def _handle_text(self, update: Any, _context: Any) -> None:
        try:
            self._check_auth(update)
        except TelegramAuthorizationError:
            await self._reply(update, "⛔ You are not authorized to use this bot.")
            return
        intent = update.effective_message.text or ""
        if not intent.strip():
            return
        await self._dispatch_intent(update, intent)

    async def _dispatch_intent(self, update: Any, intent: str) -> None:
        await self._reply(update, f"🚀 Dispatching: <code>{html.escape(intent)}</code>")
        try:
            task = await self.engine.dispatch(intent)
        except Exception as exc:  # noqa: BLE001
            await self._reply(update, f"❌ Failed to dispatch task: {html.escape(str(exc))}")
            return

        risk = self.engine._risk_level_for_task(task)
        if self.engine._requires_approval(risk) and not self.engine.approval_manager.is_approved(task.id):
            await self._send_approval_request(update, task, risk)
            return

        await self._wait_and_report(update, task.id)

    async def _send_approval_request(self, update: Any, task: AgencyTask, risk: RiskLevel) -> None:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve:{task.id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject:{task.id}"),
            ]
        ]
        await self._reply(
            update,
            f"⏸ <b>Approval required</b>\n\n"
            f"Task: <code>{html.escape(task.intent)}</code>\n"
            f"ID: <code>{task.id}</code>\n"
            f"Risk: <b>{risk.value.upper()}</b>\n\n"
            f"Use the buttons or /approve {task.id} / /reject {task.id}.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    async def _wait_and_report(self, update: Any, task_id: str) -> None:
        task = self.engine.get_task(task_id)
        if task is None:
            await self._reply(update, "❌ Task not found after dispatch.")
            return

        terminal = {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}
        elapsed = 0.0
        while task.status not in terminal and elapsed < self.max_poll_seconds:
            await asyncio.sleep(self.poll_interval)
            elapsed += self.poll_interval
            task = self.engine.get_task(task_id)
            if task is None:
                await self._reply(update, "❌ Task disappeared during execution.")
                return

        await self._reply_task(update, task)

    async def _reply_task(self, update: Any, task: AgencyTask) -> None:
        status_icon = {
            TaskStatus.COMPLETED: "✅",
            TaskStatus.FAILED: "❌",
            TaskStatus.CANCELLED: "🚫",
        }.get(task.status, "⏳")
        module_line = f"Module: <b>{html.escape(task.module_id or 'N/A')}</b>\n" if task.module_id else ""
        result_preview = ""
        if task.result:
            result_preview = f"\n<b>Result:</b>\n<pre>{html.escape(self._short_json(task.result))}</pre>"
        error_preview = ""
        if task.error:
            error_preview = f"\n<b>Error:</b>\n<pre>{html.escape(task.error[:800])}</pre>"

        await self._reply(
            update,
            f"{status_icon} <b>Task {task.status.value}</b>\n\n"
            f"ID: <code>{task.id}</code>\n"
            f"Intent: <code>{html.escape(task.intent)}</code>\n"
            f"{module_line}"
            f"Risk: {self.engine._risk_level_for_task(task).value}"
            f"{result_preview}{error_preview}",
        )

    async def _cmd_tasks(self, update: Any, _context: Any) -> None:
        try:
            self._check_auth(update)
        except TelegramAuthorizationError:
            await self._reply(update, "⛔ You are not authorized to use this bot.")
            return
        tasks = self.engine.list_tasks(limit=10)
        if not tasks:
            await self._reply(update, "No tasks yet.")
            return
        lines = ["<b>Recent tasks</b>"]
        for task in tasks:
            lines.append(f"• <code>{task.id}</code> — {task.status.value} — {html.escape(task.intent[:60])}")
        await self._reply(update, "\n".join(lines))

    async def _cmd_task(self, update: Any, _context: Any) -> None:
        try:
            self._check_auth(update)
        except TelegramAuthorizationError:
            await self._reply(update, "⛔ You are not authorized to use this bot.")
            return
        text = update.effective_message.text or ""
        parts = text.split(" ", 1)
        if len(parts) < 2 or not parts[1].strip():
            await self._reply(update, "Usage: /task &lt;id&gt;")
            return
        task_id = parts[1].strip()
        task = self.engine.get_task(task_id)
        if task is None:
            await self._reply(update, f"Task <code>{html.escape(task_id)}</code> not found.")
            return
        await self._reply_task(update, task)

    async def _cmd_approve(self, update: Any, _context: Any) -> None:
        try:
            self._check_auth(update)
        except TelegramAuthorizationError:
            await self._reply(update, "⛔ You are not authorized to use this bot.")
            return
        task_id = self._extract_task_id(update)
        if task_id is None:
            await self._reply(update, "Usage: /approve &lt;task-id&gt;")
            return
        req = await self.engine.approve_task(task_id, by=f"telegram:{update.effective_chat.id}")
        if req is None:
            await self._reply(update, f"No approval request found for <code>{html.escape(task_id)}</code>.")
            return
        await self._reply(update, f"✅ Approved <code>{html.escape(task_id)}</code>. Re-executing...")
        task = self.engine.get_task(task_id)
        if task is not None:
            await self.engine._task_queue.put(task)
            await self._wait_and_report(update, task_id)
        else:
            await self._reply(update, f"❌ Task <code>{html.escape(task_id)}</code> not found.")

    async def _cmd_reject(self, update: Any, _context: Any) -> None:
        try:
            self._check_auth(update)
        except TelegramAuthorizationError:
            await self._reply(update, "⛔ You are not authorized to use this bot.")
            return
        task_id = self._extract_task_id(update)
        if task_id is None:
            await self._reply(update, "Usage: /reject &lt;task-id&gt;")
            return
        request_id = self.engine.approval_manager._by_task.get(task_id)
        if request_id is None:
            await self._reply(update, f"No approval request found for <code>{html.escape(task_id)}</code>.")
            return
        self.engine.approval_manager.reject(request_id, by=f"telegram:{update.effective_chat.id}")
        await self._reply(update, f"❌ Rejected <code>{html.escape(task_id)}</code>.")

    async def _cmd_approvals(self, update: Any, _context: Any) -> None:
        try:
            self._check_auth(update)
        except TelegramAuthorizationError:
            await self._reply(update, "⛔ You are not authorized to use this bot.")
            return
        pending = self.engine.approval_manager.list_pending()
        if not pending:
            await self._reply(update, "No pending approvals.")
            return
        lines = ["<b>Pending approvals</b>"]
        for req in pending:
            lines.append(
                f"• <code>{req.task_id}</code> — {req.risk_level.value.upper()}\n  {html.escape(req.reason[:120])}"
            )
        await self._reply(update, "\n".join(lines))

    async def _cmd_stats(self, update: Any, _context: Any) -> None:
        try:
            self._check_auth(update)
        except TelegramAuthorizationError:
            await self._reply(update, "⛔ You are not authorized to use this bot.")
            return
        stats = self.engine.stats()
        reg = stats.get("registry", {})
        await self._reply(
            update,
            "<b>Agency Stats</b>\n\n"
            f"Modules: <b>{reg.get('total_modules', 0)}</b>\n"
            f"Active: <b>{reg.get('active', 0)}</b>\n"
            f"Total Stars: <b>{reg.get('total_stars', 0)}</b>\n"
            f"Memory Events: <b>{stats.get('memory_events', 0)}</b>",
        )

    async def _cmd_registry(self, update: Any, _context: Any) -> None:
        try:
            self._check_auth(update)
        except TelegramAuthorizationError:
            await self._reply(update, "⛔ You are not authorized to use this bot.")
            return
        modules = sorted(self.engine.registry.modules, key=lambda m: m.stars, reverse=True)[:15]
        if not modules:
            await self._reply(update, "Registry is empty. Run /sync first.")
            return
        lines = ["<b>Top modules</b>"]
        for mod in modules:
            lines.append(
                f"• <b>{html.escape(mod.name)}</b> ({mod.category.value}) — ⭐ {mod.stars}\n"
                f"  {html.escape(mod.description or '')[:80]}"
            )
        await self._reply(update, "\n".join(lines))

    async def _callback_approve(self, update: Any, context: Any) -> None:
        query = update.callback_query
        await query.answer()
        try:
            self._check_auth(update)
        except TelegramAuthorizationError:
            await query.edit_message_text("⛔ You are not authorized to use this bot.")
            return
        task_id = query.data.split(":", 1)[1]
        req = await self.engine.approve_task(task_id, by=f"telegram:{update.effective_chat.id}")
        if req is None:
            await query.edit_message_text(f"No approval request found for <code>{html.escape(task_id)}</code>.")
            return
        await query.edit_message_text(f"✅ Approved <code>{html.escape(task_id)}</code>. Executing...")
        task = self.engine.get_task(task_id)
        if task is not None:
            await self.engine._task_queue.put(task)
            await self._wait_and_report(update, task_id)
        else:
            await query.edit_message_text(f"❌ Task <code>{html.escape(task_id)}</code> not found.")

    async def _callback_reject(self, update: Any, _context: Any) -> None:
        query = update.callback_query
        await query.answer()
        try:
            self._check_auth(update)
        except TelegramAuthorizationError:
            await query.edit_message_text("⛔ You are not authorized to use this bot.")
            return
        task_id = query.data.split(":", 1)[1]
        request_id = self.engine.approval_manager._by_task.get(task_id)
        if request_id is None:
            await query.edit_message_text(f"No approval request found for <code>{html.escape(task_id)}</code>.")
            return
        self.engine.approval_manager.reject(request_id, by=f"telegram:{update.effective_chat.id}")
        await query.edit_message_text(f"❌ Rejected <code>{html.escape(task_id)}</code>.")

    def _extract_task_id(self, update: Any) -> str | None:
        text = update.effective_message.text or ""
        parts = text.split(" ", 1)
        if len(parts) < 2:
            return None
        task_id = parts[1].strip()
        return task_id if task_id else None

    @staticmethod
    def _short_json(value: Any, max_len: int = 800) -> str:
        import json

        text = json.dumps(value, indent=2, default=str)
        if len(text) > max_len:
            text = text[:max_len] + "\n..."
        return text

    async def _reply(self, update: Any, text: str, parse_mode: str = "HTML", reply_markup: Any = None) -> None:
        await update.effective_message.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup)


def run_bot(
    token: str | None = None,
    config: AgencyConfig | None = None,
    engine: AgencyEngine | None = None,
) -> None:
    """CLI entrypoint for the general agency Telegram bot."""
    token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("Telegram bot token is required (pass --token or set TELEGRAM_BOT_TOKEN)")

    config = config or AgencyConfig()
    if config.telegram.token and not token:
        token = config.telegram.token

    bot = AgencyTelegramBot(token=token, engine=engine, config=config)
    asyncio.run(bot.run())
