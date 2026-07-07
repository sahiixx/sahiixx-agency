"""Notification manager for the agency."""

from __future__ import annotations

import asyncio
import contextlib
import os
import uuid
from collections import deque
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from .models import BusMessage, Notification, NotificationChannel

NotificationHandler = Callable[[Notification], None]


class NotificationManager:
    """Multi-channel notification dispatcher with in-memory history.

    Supported channels:
    - telegram: send via a configured Telegram bot token/chat id.
    - email: SMTP send (requires config).
    - webhook: POST JSON to an external URL.
    - sse: push to dashboard listeners.
    - console: log to stdout (fallback / dev mode).
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self._history: deque[Notification] = deque(maxlen=1000)
        self._listeners: list[NotificationHandler] = []
        self._lock = asyncio.Lock()
        self._telegram_app: Any | None = None

    def subscribe(self, handler: NotificationHandler) -> None:
        """Subscribe to every notification (used by SSE broadcaster)."""
        self._listeners.append(handler)

    def unsubscribe(self, handler: NotificationHandler) -> None:
        with __import__("contextlib").suppress(ValueError):
            self._listeners.remove(handler)

    async def send(
        self,
        channel: NotificationChannel,
        title: str,
        body: str,
        recipient: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Notification:
        """Send a notification through the requested channel."""
        notification = Notification(
            id=f"ntf_{uuid.uuid4().hex[:8]}",
            channel=channel,
            title=title,
            body=body,
            recipient=recipient,
            payload=payload or {},
        )
        async with self._lock:
            self._history.append(notification)

        # SSE and console are synchronous local channels.
        if channel in {NotificationChannel.SSE, NotificationChannel.CONSOLE}:
            notification.status = "sent"
            notification.sent_at = datetime.now(timezone.utc)

        # Dispatch to external channels concurrently.
        if channel == NotificationChannel.TELEGRAM:
            await self._send_telegram(notification)
        elif channel == NotificationChannel.EMAIL:
            await self._send_email(notification)
        elif channel == NotificationChannel.WEBHOOK:
            await self._send_webhook(notification)

        # Broadcast to in-process listeners.
        for handler in list(self._listeners):
            with contextlib.suppress(Exception):
                handler(notification)

        return notification

    async def broadcast(
        self,
        title: str,
        body: str,
        channels: list[NotificationChannel] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> list[Notification]:
        """Send the same notification to multiple channels."""
        channels = channels or [NotificationChannel.SSE]
        tasks = [
            self.send(ch, title, body, payload=payload)
            for ch in channels
        ]
        return await asyncio.gather(*tasks)

    async def on_bus_message(self, message: BusMessage) -> None:
        """Auto-notify on interesting bus events."""
        topic = message.topic
        payload = message.payload

        if topic == "task.failed":
            await self.broadcast(
                f"Task failed: {payload.get('task_id', 'unknown')}",
                payload.get("error") or "Task execution failed.",
                channels=self._auto_channels(),
                payload=payload,
            )
        elif topic == "task.awaiting_approval":
            task_id = payload.get("task_id", "unknown")
            await self.broadcast(
                f"Approval required: {task_id}",
                f"Task {task_id} is awaiting approval. Reply /approve {task_id}",
                channels=self._auto_channels(),
                payload=payload,
            )
        elif topic == "task.completed":
            task_id = payload.get("task_id", "unknown")
            await self.broadcast(
                f"Task completed: {task_id}",
                f"Task {task_id} finished successfully.",
                channels=[NotificationChannel.SSE],
                payload=payload,
            )

    def history(self, channel: NotificationChannel | None = None, limit: int = 100) -> list[Notification]:
        """Return recent notifications, optionally filtered by channel."""
        msgs = list(self._history)
        if channel:
            msgs = [m for m in msgs if m.channel == channel]
        return msgs[-limit:]

    def _auto_channels(self) -> list[NotificationChannel]:
        channels: list[NotificationChannel] = [NotificationChannel.SSE]
        cfg = self.config
        if cfg.get("telegram", {}).get("enabled"):
            channels.append(NotificationChannel.TELEGRAM)
        if cfg.get("email", {}).get("enabled"):
            channels.append(NotificationChannel.EMAIL)
        if cfg.get("webhook", {}).get("enabled"):
            channels.append(NotificationChannel.WEBHOOK)
        return channels

    async def _send_telegram(self, notification: Notification) -> None:
        token = self.config.get("telegram", {}).get("token") or os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = notification.recipient or self.config.get("telegram", {}).get("chat_id")
        if not token or not chat_id:
            notification.status = "failed"
            notification.error = "Telegram token or chat_id not configured"
            return

        try:
            import httpx

            text = f"*{notification.title}*\n{notification.body}"
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    url,
                    json={
                        "chat_id": chat_id,
                        "text": text,
                        "parse_mode": "Markdown",
                    },
                )
            if resp.status_code == 200:
                notification.status = "sent"
                notification.sent_at = datetime.now(timezone.utc)
            else:
                notification.status = "failed"
                notification.error = f"HTTP {resp.status_code}: {resp.text[:200]}"
        except Exception as exc:  # noqa: BLE001
            notification.status = "failed"
            notification.error = str(exc)

    async def _send_email(self, notification: Notification) -> None:
        email_cfg = self.config.get("email", {})
        smtp_host = email_cfg.get("smtp_host")
        smtp_port = email_cfg.get("smtp_port", 587)
        smtp_user = email_cfg.get("smtp_user") or os.environ.get("SMTP_USER")
        smtp_password = email_cfg.get("smtp_password") or os.environ.get("SMTP_PASSWORD")
        to_addr = notification.recipient or email_cfg.get("default_recipient")

        if not all([smtp_host, smtp_user, smtp_password, to_addr]):
            notification.status = "failed"
            notification.error = "Email SMTP settings incomplete"
            return

        try:
            import smtplib
            from email.message import EmailMessage

            msg = EmailMessage()
            msg["From"] = smtp_user
            msg["To"] = to_addr
            msg["Subject"] = notification.title
            msg.set_content(notification.body)

            def _send() -> None:
                assert isinstance(smtp_host, str)
                assert isinstance(smtp_user, str)
                assert isinstance(smtp_password, str)
                with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                    server.send_message(msg)

            await asyncio.to_thread(_send)
            notification.status = "sent"
            notification.sent_at = datetime.now(timezone.utc)
        except Exception as exc:  # noqa: BLE001
            notification.status = "failed"
            notification.error = str(exc)

    async def _send_webhook(self, notification: Notification) -> None:
        webhook_cfg = self.config.get("webhook", {})
        url = notification.recipient or webhook_cfg.get("url")
        if not url:
            notification.status = "failed"
            notification.error = "Webhook URL not configured"
            return

        try:
            import httpx

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    url,
                    json={
                        "title": notification.title,
                        "body": notification.body,
                        "payload": notification.payload,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
            if resp.status_code < 400:
                notification.status = "sent"
                notification.sent_at = datetime.now(timezone.utc)
            else:
                notification.status = "failed"
                notification.error = f"HTTP {resp.status_code}: {resp.text[:200]}"
        except Exception as exc:  # noqa: BLE001
            notification.status = "failed"
            notification.error = str(exc)
