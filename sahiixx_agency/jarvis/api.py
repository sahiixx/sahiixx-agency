"""Jarvis API — FastAPI endpoints for web and WebSocket access."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from pydantic import BaseModel

from .agent import JarvisAgent
from .models import JarvisMessage, MessageType

router = APIRouter(prefix="/jarvis", tags=["jarvis"])

# Global agent instance
_agent: JarvisAgent | None = None


def get_agent() -> JarvisAgent:
    """Get or create the global Jarvis agent."""
    global _agent
    if _agent is None:
        _agent = JarvisAgent()
    return _agent


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""

    message: str
    message_type: str = "text"


class ChatResponse(BaseModel):
    """Response body for chat endpoint."""

    content: str
    action: str | None = None
    confidence: float = 1.0


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Process a chat message."""
    agent = get_agent()

    msg_type = MessageType(request.message_type) if request.message_type in MessageType.__members__.values() else MessageType.TEXT

    message = JarvisMessage(
        content=request.message,
        message_type=msg_type,
    )

    response = await agent.process_message(message)

    return ChatResponse(
        content=response.content,
        action=response.action,
        confidence=response.confidence,
    )


@router.get("/status")
async def status() -> dict[str, Any]:
    """Get Jarvis status."""
    agent = get_agent()
    return {
        "mode": agent.state.mode.value,
        "session_id": agent.state.session_id,
        "turn_count": agent.state.turn_count,
        "context_size": len(agent.state.context),
        "events_count": len(agent.state.events),
    }


@router.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "jarvis"}


@router.get("/events")
async def events(limit: int = 10) -> list[dict[str, Any]]:
    """Get recent monitoring events."""
    agent = get_agent()
    events = agent.get_recent_events(limit=limit)
    return [e.model_dump() for e in events]


@router.post("/start")
async def start() -> dict[str, str]:
    """Start the Jarvis agent."""
    agent = get_agent()
    await agent.start()
    return {"status": "started", "session_id": agent.state.session_id}


@router.post("/stop")
async def stop() -> dict[str, str]:
    """Stop the Jarvis agent."""
    agent = get_agent()
    await agent.stop()
    return {"status": "stopped"}


# ─── WebSocket for real-time chat ──────────────────────────────


class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.remove(websocket)

    async def send_message(self, message: str, websocket: WebSocket) -> None:
        await websocket.send_text(message)


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time chat."""
    await manager.connect(websocket)
    agent = get_agent()

    try:
        while True:
            # Receive message
            data = await websocket.receive_text()

            # Process message
            message = JarvisMessage(
                content=data,
                message_type=MessageType.TEXT,
            )

            response = await agent.process_message(message)

            # Send response
            await manager.send_message(
                response.model_dump_json(),
                websocket,
            )

    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ─── ElevenLabs TTS endpoint ──────────────────────────────────


class TTSRequest(BaseModel):
    """Request body for TTS endpoint."""

    text: str
    voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # Default ElevenLabs voice


@router.post("/tts")
async def text_to_speech(request: TTSRequest) -> Response:
    """Convert text to speech using ElevenLabs API."""
    try:
        import httpx

        api_key = os.environ.get("ELEVENLABS_API_KEY")
        if not api_key:
            return Response(
                content='{"error": "ELEVENLABS_API_KEY not set"}',
                status_code=500,
                media_type="application/json",
            )

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{request.voice_id}",
                headers={
                    "xi-api-key": api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "text": request.text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75,
                        "style": 0.5,
                        "use_speaker_boost": True,
                    },
                },
            )
            response.raise_for_status()
            return Response(
                content=response.content,
                media_type="audio/mpeg",
            )

    except Exception as e:
        return Response(
            content=f'{{"error": "{str(e)}"}}',
            status_code=500,
            media_type="application/json",
        )
