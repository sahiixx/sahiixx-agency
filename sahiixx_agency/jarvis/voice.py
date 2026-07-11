"""Voice pipeline — Whisper for STT, multiple TTS providers."""

from __future__ import annotations

import io
import os
from typing import Any

from .models import JarvisConfig


class VoicePipeline:
    """Handles voice input (STT) and output (TTS)."""

    def __init__(self, config: JarvisConfig) -> None:
        self.config = config
        self._client: Any = None

    async def transcribe(self, audio_data: bytes, language: str = "en") -> str:
        """Transcribe audio to text using OpenAI Whisper.

        Args:
            audio_data: Raw audio bytes (WAV, MP3, etc.)
            language: Language code (e.g., 'en', 'ar', 'fr')

        Returns:
            Transcribed text.
        """
        if not self.config.voice_enabled:
            return ""

        try:
            import httpx

            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set for voice transcription")

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    files={"file": ("audio.wav", io.BytesIO(audio_data), "audio/wav")},
                    data={
                        "model": self.config.whisper_model,
                        "language": language,
                    },
                )
                response.raise_for_status()
                return response.json().get("text", "")

        except ImportError:
            raise ImportError("httpx required for voice pipeline: pip install httpx")
        except Exception as e:
            raise RuntimeError(f"Transcription failed: {e}")

    async def synthesize(self, text: str, voice: str | None = None) -> bytes:
        """Synthesize text to speech.

        Args:
            text: Text to speak.
            voice: Voice ID (overrides config default).

        Returns:
            Audio bytes (MP3 format).
        """
        if not self.config.voice_enabled:
            return b""

        voice = voice or self.config.tts_voice

        if self.config.tts_provider == "openai":
            return await self._openai_tts(text, voice)
        elif self.config.tts_provider == "elevenlabs":
            return await self._elevenlabs_tts(text, voice)
        else:
            raise ValueError(f"Unknown TTS provider: {self.config.tts_provider}")

    async def _openai_tts(self, text: str, voice: str) -> bytes:
        """OpenAI TTS API."""
        try:
            import httpx

            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set for TTS")

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    "https://api.openai.com/v1/audio/speech",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": "tts-1",
                        "input": text,
                        "voice": voice,
                    },
                )
                response.raise_for_status()
                return response.content

        except Exception as e:
            raise RuntimeError(f"OpenAI TTS failed: {e}")

    async def _elevenlabs_tts(self, text: str, voice_id: str) -> bytes:
        """ElevenLabs TTS API."""
        try:
            import httpx

            api_key = os.environ.get("ELEVENLABS_API_KEY")
            if not api_key:
                raise ValueError("ELEVENLABS_API_KEY not set for TTS")

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                    headers={
                        "xi-api-key": api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "text": text,
                        "model_id": "eleven_monolingual_v1",
                    },
                )
                response.raise_for_status()
                return response.content

        except Exception as e:
            raise RuntimeError(f"ElevenLabs TTS failed: {e}")

    async def speak(self, text: str) -> None:
        """Synthesize and play audio (requires pygame or similar).

        This is a convenience method for CLI usage.
        In production, audio playback should be handled by the frontend.
        """
        if not self.config.voice_enabled:
            print(text)
            return

        try:
            audio = await self.synthesize(text)
            if audio:
                # Try to play with pygame
                try:
                    import pygame

                    pygame.mixer.init()
                    sound = pygame.mixer.Sound(io.BytesIO(audio))
                    sound.play()
                    while pygame.mixer.get_busy():
                        await asyncio.sleep(0.1)
                except ImportError:
                    # Fallback: save to temp file
                    import tempfile
                    import subprocess

                    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                        f.write(audio)
                        temp_path = f.name

                    # Try to play with system player
                    try:
                        subprocess.run(["start", temp_path], shell=True, check=True)
                    except Exception:
                        print(f"[Audio saved to {temp_path}]")
        except Exception as e:
            print(f"Voice playback failed: {e}")
            print(text)


# Import asyncio for the speak method
import asyncio  # noqa: E402
