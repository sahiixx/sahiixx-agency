"""Jarvis data models."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class JarvisMode(str, Enum):
    """Jarvis operating modes."""

    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    EXECUTING = "executing"
    MONITORING = "monitoring"


class MessageType(str, Enum):
    """Types of messages Jarvis can handle."""

    VOICE = "voice"
    TEXT = "text"
    SYSTEM = "system"
    PROACTIVE = "proactive"
    ALERT = "alert"


class JarvisMessage(BaseModel):
    """A message sent to or from Jarvis."""

    id: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    content: str
    message_type: MessageType = MessageType.TEXT
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)
    context: list[str] = Field(default_factory=list)


class JarvisResponse(BaseModel):
    """Jarvis response to a message."""

    content: str
    action: str | None = None
    action_data: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    sources: list[str] = Field(default_factory=list)
    follow_up: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class JarvisConfig(BaseModel):
    """Jarvis configuration."""

    name: str = "Jarvis"
    voice_enabled: bool = False
    whisper_model: str = "whisper-1"
    tts_provider: str = "openai"  # openai, elevenlabs, azure
    tts_voice: str = "alloy"
    proactive_monitoring: bool = True
    monitor_interval_seconds: int = 300  # 5 minutes
    max_context_turns: int = 20
    temperature: float = 0.7
    system_prompt: str = ""
    allowed_commands: list[str] = Field(default_factory=list)
    blocked_commands: list[str] = Field(default_factory=list)


class MonitorEvent(BaseModel):
    """An event detected by the monitoring system."""

    event_type: str
    severity: str = "info"  # info, warning, critical
    source: str
    title: str
    description: str
    suggested_action: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class JarvisState(BaseModel):
    """Current state of the Jarvis agent."""

    mode: JarvisMode = JarvisMode.IDLE
    session_id: str = ""
    turn_count: int = 0
    total_tokens: int = 0
    last_activity: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    active_task: str | None = None
    context: list[JarvisMessage] = Field(default_factory=list)
    events: list[MonitorEvent] = Field(default_factory=list)
