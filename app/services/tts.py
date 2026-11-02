"""Text-to-speech stage."""
from typing import Protocol


class TTS(Protocol):
    async def synthesize(self, text: str, language: str) -> bytes: ...


class DevTTS:
    """Dev stand-in: returns the text as bytes. Real impl should return Opus-encoded audio
    at an aggressive bitrate (~16-24 kbps) for low-bandwidth networks."""

    async def synthesize(self, text: str, language: str) -> bytes:
        return text.encode("utf-8")
