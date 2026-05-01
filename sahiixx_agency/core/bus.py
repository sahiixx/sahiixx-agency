"""Async message bus for inter-module communication."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Callable

from .models import BusMessage


type Handler = Callable[[BusMessage], None]


class MessageBus:
    """In-memory pub/sub message bus with optional persistence."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)
        self._history: list[BusMessage] = []
        self._lock = asyncio.Lock()

    def subscribe(self, topic: str, handler: Handler) -> None:
        self._handlers[topic].append(handler)

    def unsubscribe(self, topic: str, handler: Handler) -> None:
        if topic in self._handlers:
            try:
                self._handlers[topic].remove(handler)
            except ValueError:
                pass

    async def publish(self, message: BusMessage) -> None:
        async with self._lock:
            self._history.append(message)
        # Notify all subscribers
        handlers = self._handlers.get(message.topic, [])
        for handler in handlers:
            try:
                handler(message)
            except Exception:
                pass
        # Also notify wildcards
        for handler in self._handlers.get("*", []):
            try:
                handler(message)
            except Exception:
                pass

    def history(self, topic: str | None = None, limit: int = 100) -> list[BusMessage]:
        msgs = self._history if topic is None else [m for m in self._history if m.topic == topic]
        return msgs[-limit:]
