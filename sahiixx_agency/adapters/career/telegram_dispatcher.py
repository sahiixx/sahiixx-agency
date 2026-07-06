"""Telegram dispatcher for Career-Ops job postings."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from typing import Any

URL_RE = re.compile(r"https?://\S+")


def _default_command_builder(url: str, use_claude: bool = False) -> list[str]:
    """Return the default command list to dispatch a URL to Career-Ops."""
    if use_claude:
        return ["claude", "-p", f"/career-ops oferta {url}"]
    return ["cops", "oferta", url]


@dataclass
class DispatchResult:
    """Result of dispatching a URL to Career-Ops."""

    ok: bool
    stdout: str
    stderr: str
    command: str
    returncode: int


class CareerOpsDispatcher:
    """Dispatch job posting URLs to a Career-Ops runner and format replies."""

    def __init__(
        self,
        command_builder: Any = None,
        use_claude: bool = False,
        timeout: int = 300,
    ) -> None:
        self.command_builder = command_builder or _default_command_builder
        self.use_claude = use_claude
        self.timeout = timeout

    def dispatch(self, url: str) -> DispatchResult:
        """Run the Career-Ops command for a URL and capture output."""
        try:
            cmd = self.command_builder(url, self.use_claude)
            command = " ".join(cmd)
        except Exception as exc:  # noqa: BLE001
            return DispatchResult(
                ok=False,
                stdout="",
                stderr=str(exc),
                command="",
                returncode=-1,
            )

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
            )
            return DispatchResult(
                ok=proc.returncode == 0,
                stdout=proc.stdout,
                stderr=proc.stderr,
                command=command,
                returncode=proc.returncode,
            )
        except subprocess.TimeoutExpired as exc:
            return DispatchResult(
                ok=False,
                stdout=str(exc.stdout or ""),
                stderr=str(exc.stderr or ""),
                command=command,
                returncode=-1,
            )
        except Exception as exc:  # noqa: BLE001
            return DispatchResult(
                ok=False,
                stdout="",
                stderr=str(exc),
                command=command,
                returncode=-1,
            )

    @staticmethod
    def extract_url(text: str) -> str | None:
        """Return the first URL found in ``text``, or ``None``."""
        match = URL_RE.search(text)
        return match.group(0) if match else None

    @staticmethod
    def format_reply(result: DispatchResult) -> str:
        """Format a short HTML reply from the dispatch result."""
        status = "✅ Done" if result.ok else "❌ Failed"
        reply = f"{status}\n<b>Command:</b> <code>{result.command}</code>"
        if result.stdout:
            snippet = result.stdout.strip()[:1200]
            reply += f"\n\n<b>Output:</b>\n<pre>{snippet}</pre>"
        if not result.ok and result.stderr:
            err = result.stderr.strip()[:600]
            reply += f"\n\n<b>Error:</b>\n<pre>{err}</pre>"
        return reply


class CareerOpsTelegramBot:
    """Run a Telegram bot that forwards job URLs to Career-Ops."""

    def __init__(
        self,
        token: str,
        dispatcher: CareerOpsDispatcher | None = None,
        dry_run: bool = False,
    ) -> None:
        self.token = token
        self.dispatcher = dispatcher or CareerOpsDispatcher()
        self.dry_run = dry_run

    def _build_app(self) -> Any:
        from telegram.ext import ApplicationBuilder

        return ApplicationBuilder().token(self.token).build()

    async def run(self) -> None:
        """Start polling for Telegram messages."""
        from telegram.ext import CommandHandler, MessageHandler, filters

        application = self._build_app()
        application.bot_data["dispatcher"] = self.dispatcher
        application.bot_data["dry_run"] = self.dry_run

        async def start(update: Any, _context: Any) -> None:
            await update.effective_message.reply_text(
                "Send me a job posting URL and I'll run Career-Ops on it.\n"
                "Use /help for more info."
            )

        async def help_command(update: Any, _context: Any) -> None:
            await update.effective_message.reply_text(
                "Paste any job posting URL. The bot will dispatch it to Career-Ops\n"
                "and return the evaluation summary."
            )

        async def handle_message(update: Any, context: Any) -> None:
            text = update.effective_message.text or ""
            url = CareerOpsDispatcher.extract_url(text)
            if not url:
                await update.effective_message.reply_text("I need a URL to a job posting.")
                return

            await update.effective_message.reply_text(f"Dispatching Career-Ops for {url}...")

            if context.bot_data.get("dry_run"):
                cmd = " ".join(_default_command_builder(url))
                await update.effective_message.reply_text(f"[DRY RUN] Would run: {cmd}")
                return

            dispatcher: CareerOpsDispatcher = context.bot_data["dispatcher"]
            result = dispatcher.dispatch(url)
            await update.effective_message.reply_text(
                CareerOpsDispatcher.format_reply(result),
                parse_mode="HTML",
            )

        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        await application.run_polling()

    def run_sync(self) -> None:
        """Start polling synchronously (used by the CLI)."""
        from telegram.ext import CommandHandler, MessageHandler, filters

        application = self._build_app()
        application.bot_data["dispatcher"] = self.dispatcher
        application.bot_data["dry_run"] = self.dry_run

        async def start(update: Any, _context: Any) -> None:
            await update.effective_message.reply_text(
                "Send me a job posting URL and I'll run Career-Ops on it.\n"
                "Use /help for more info."
            )

        async def help_command(update: Any, _context: Any) -> None:
            await update.effective_message.reply_text(
                "Paste any job posting URL. The bot will dispatch it to Career-Ops\n"
                "and return the evaluation summary."
            )

        async def handle_message(update: Any, context: Any) -> None:
            text = update.effective_message.text or ""
            url = CareerOpsDispatcher.extract_url(text)
            if not url:
                await update.effective_message.reply_text("I need a URL to a job posting.")
                return

            await update.effective_message.reply_text(f"Dispatching Career-Ops for {url}...")

            if context.bot_data.get("dry_run"):
                cmd = " ".join(_default_command_builder(url))
                await update.effective_message.reply_text(f"[DRY RUN] Would run: {cmd}")
                return

            dispatcher: CareerOpsDispatcher = context.bot_data["dispatcher"]
            result = dispatcher.dispatch(url)
            await update.effective_message.reply_text(
                CareerOpsDispatcher.format_reply(result),
                parse_mode="HTML",
            )

        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        application.run_polling()


def run_bot(
    token: str | None = None,
    dry_run: bool = False,
    use_claude: bool = False,
) -> None:
    """Entrypoint used by the CLI."""
    token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("Telegram bot token is required (pass --token or set TELEGRAM_BOT_TOKEN)")
    dispatcher = CareerOpsDispatcher(use_claude=use_claude)
    bot = CareerOpsTelegramBot(token=token, dispatcher=dispatcher, dry_run=dry_run)
    bot.run_sync()
