"""Tests for the Jarvis module."""

from __future__ import annotations

import pytest

from sahiixx_agency.jarvis.agent import JarvisAgent
from sahiixx_agency.jarvis.models import (
    JarvisConfig,
    JarvisMessage,
    JarvisResponse,
    JarvisState,
    MessageType,
    MonitorEvent,
)


class TestJarvisConfig:
    """Tests for JarvisConfig model."""

    def test_default_config(self) -> None:
        config = JarvisConfig()
        assert config.name == "Jarvis"
        assert config.voice_enabled is False
        assert config.proactive_monitoring is True
        assert config.monitor_interval_seconds == 300

    def test_custom_config(self) -> None:
        config = JarvisConfig(
            name="Friday",
            voice_enabled=True,
            tts_provider="elevenlabs",
            monitor_interval_seconds=60,
        )
        assert config.name == "Friday"
        assert config.voice_enabled is True
        assert config.tts_provider == "elevenlabs"
        assert config.monitor_interval_seconds == 60


class TestJarvisMessage:
    """Tests for JarvisMessage model."""

    def test_create_message(self) -> None:
        msg = JarvisMessage(content="Hello Jarvis")
        assert msg.content == "Hello Jarvis"
        assert msg.message_type == MessageType.TEXT
        assert msg.id is not None
        assert msg.timestamp is not None

    def test_voice_message(self) -> None:
        msg = JarvisMessage(
            content="What's the status?",
            message_type=MessageType.VOICE,
        )
        assert msg.message_type == MessageType.VOICE

    def test_message_with_metadata(self) -> None:
        msg = JarvisMessage(
            content="Test",
            metadata={"source": "telegram", "chat_id": "123"},
        )
        assert msg.metadata["source"] == "telegram"
        assert msg.metadata["chat_id"] == "123"


class TestJarvisResponse:
    """Tests for JarvisResponse model."""

    def test_create_response(self) -> None:
        resp = JarvisResponse(content="Hello! How can I help?")
        assert resp.content == "Hello! How can I help?"
        assert resp.action is None
        assert resp.confidence == 1.0

    def test_response_with_action(self) -> None:
        resp = JarvisResponse(
            content="Task dispatched",
            action="task_dispatched",
            action_data={"task_id": "abc123"},
        )
        assert resp.action == "task_dispatched"
        assert resp.action_data["task_id"] == "abc123"


class TestJarvisAgent:
    """Tests for JarvisAgent."""

    @pytest.mark.asyncio
    async def test_agent_start_stop(self) -> None:
        agent = JarvisAgent(JarvisConfig(proactive_monitoring=False))
        await agent.start()
        assert agent.state.session_id is not None
        await agent.stop()
        assert len(agent.state.events) > 0  # Should have start/stop events

    @pytest.mark.asyncio
    async def test_process_text_message(self) -> None:
        agent = JarvisAgent(JarvisConfig(proactive_monitoring=False))
        await agent.start()

        msg = JarvisMessage(content="Hello", message_type=MessageType.TEXT)
        response = await agent.process_message(msg)

        assert isinstance(response, JarvisResponse)
        assert response.content is not None
        assert agent.state.turn_count == 1

        await agent.stop()

    @pytest.mark.asyncio
    async def test_help_command(self) -> None:
        agent = JarvisAgent(JarvisConfig(proactive_monitoring=False))
        await agent.start()

        msg = JarvisMessage(content="help", message_type=MessageType.TEXT)
        response = await agent.process_message(msg)

        assert "Jarvis Commands" in response.content
        assert "status" in response.content
        assert "dispatch" in response.content

        await agent.stop()

    @pytest.mark.asyncio
    async def test_status_command(self) -> None:
        agent = JarvisAgent(JarvisConfig(proactive_monitoring=False))
        await agent.start()

        msg = JarvisMessage(content="status", message_type=MessageType.TEXT)
        response = await agent.process_message(msg)

        assert "Jarvis Status" in response.content
        assert "Session:" in response.content

        await agent.stop()

    @pytest.mark.asyncio
    async def test_clear_command(self) -> None:
        agent = JarvisAgent(JarvisConfig(proactive_monitoring=False))
        await agent.start()

        # Add some context
        msg1 = JarvisMessage(content="Hello", message_type=MessageType.TEXT)
        await agent.process_message(msg1)
        context_len_before = len(agent.state.context)
        assert context_len_before > 0

        # Clear
        msg2 = JarvisMessage(content="clear", message_type=MessageType.TEXT)
        response = await agent.process_message(msg2)

        assert "Context cleared" in response.content
        # After clear, context should be shorter (the clear response is added back)
        assert len(agent.state.context) < context_len_before

        await agent.stop()

    @pytest.mark.asyncio
    async def test_context_command(self) -> None:
        agent = JarvisAgent(JarvisConfig(proactive_monitoring=False))
        await agent.start()

        msg1 = JarvisMessage(content="Hello", message_type=MessageType.TEXT)
        await agent.process_message(msg1)

        msg2 = JarvisMessage(content="context", message_type=MessageType.TEXT)
        response = await agent.process_message(msg2)

        assert "Context" in response.content

        await agent.stop()

    @pytest.mark.asyncio
    async def test_turn_count_increments(self) -> None:
        agent = JarvisAgent(JarvisConfig(proactive_monitoring=False))
        await agent.start()

        for i in range(3):
            msg = JarvisMessage(content=f"Message {i}", message_type=MessageType.TEXT)
            await agent.process_message(msg)

        assert agent.state.turn_count == 3

        await agent.stop()

    @pytest.mark.asyncio
    async def test_context_window_limit(self) -> None:
        config = JarvisConfig(
            proactive_monitoring=False,
            max_context_turns=5,
        )
        agent = JarvisAgent(config)
        await agent.start()

        for i in range(10):
            msg = JarvisMessage(content=f"Message {i}", message_type=MessageType.TEXT)
            await agent.process_message(msg)

        # Context is trimmed after each message add, but can be 1 over
        # temporarily because trim happens before append. Final state
        # should be close to max_context_turns.
        assert len(agent.state.context) <= config.max_context_turns + 1

        await agent.stop()


class TestMonitorEvent:
    """Tests for MonitorEvent model."""

    def test_create_event(self) -> None:
        event = MonitorEvent(
            event_type="health",
            severity="warning",
            source="jarvis",
            title="API Offline",
            description="Could not connect to API server",
        )
        assert event.severity == "warning"
        assert event.suggested_action is None

    def test_event_with_action(self) -> None:
        event = MonitorEvent(
            event_type="health",
            severity="critical",
            source="jarvis",
            title="MCP Offline",
            description="Could not connect to MCP server",
            suggested_action="Restart the MCP service",
        )
        assert event.suggested_action == "Restart the MCP service"


class TestJarvisState:
    """Tests for JarvisState model."""

    def test_default_state(self) -> None:
        state = JarvisState()
        assert state.mode.value == "idle"
        assert state.turn_count == 0
        assert state.context == []
        assert state.events == []

    def test_state_with_events(self) -> None:
        state = JarvisState()
        event = MonitorEvent(
            event_type="test",
            severity="info",
            source="test",
            title="Test Event",
            description="Test description",
        )
        state.events.append(event)
        assert len(state.events) == 1
