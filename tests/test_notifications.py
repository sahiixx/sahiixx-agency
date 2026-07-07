"""Tests for the notification manager."""

from __future__ import annotations

import pytest

from sahiixx_agency.core.models import NotificationChannel
from sahiixx_agency.core.notifications import NotificationManager


@pytest.fixture
def manager():
    return NotificationManager()


@pytest.mark.asyncio
async def test_send_sse_notification(manager):
    received = []
    manager.subscribe(lambda n: received.append(n))
    notification = await manager.send(NotificationChannel.SSE, "Hello", "World")
    assert notification.status == "sent"
    assert notification.channel == NotificationChannel.SSE
    assert len(received) == 1
    assert received[0].title == "Hello"


@pytest.mark.asyncio
async def test_broadcast_to_multiple_channels(manager):
    received = []
    manager.subscribe(lambda n: received.append(n))
    notifications = await manager.broadcast("Title", "Body", channels=[NotificationChannel.SSE, NotificationChannel.CONSOLE])
    assert len(notifications) == 2
    assert all(n.status == "sent" for n in notifications)


@pytest.mark.asyncio
async def test_telegram_fails_without_config(manager):
    notification = await manager.send(NotificationChannel.TELEGRAM, "Hello", "World")
    assert notification.status == "failed"
    assert "token" in (notification.error or "").lower() or "chat" in (notification.error or "").lower()


@pytest.mark.asyncio
async def test_webhook_fails_without_url(manager):
    notification = await manager.send(NotificationChannel.WEBHOOK, "Hello", "World")
    assert notification.status == "failed"
    assert "url" in (notification.error or "").lower()


def test_history_filters_by_channel(manager):
    import asyncio

    asyncio.run(manager.send(NotificationChannel.SSE, "A", "B"))
    asyncio.run(manager.send(NotificationChannel.CONSOLE, "C", "D"))
    sse_history = manager.history(channel=NotificationChannel.SSE)
    assert len(sse_history) == 1
    assert sse_history[0].title == "A"


@pytest.mark.asyncio
async def test_on_bus_message_sends_failure_notification(manager):
    received = []
    manager.subscribe(lambda n: received.append(n))
    from sahiixx_agency.core.models import BusMessage

    message = BusMessage(id="msg_1", topic="task.failed", sender="test", payload={"task_id": "task_1", "error": "boom"})
    await manager.on_bus_message(message)
    assert any(n.title.startswith("Task failed") for n in received)
