"""Speech-to-text stage. Swap vendors by implementing the STT protocol."""
from typing import Protocol


class STT(Protocol):
    async def transcribe(self, audio: bytes, language: str) -> str: ...


class DevSTT:
    """Dev stand-in: treats the uploaded bytes as UTF-8 text so you can test the pipeline
    without a vendor. Replace with a real provider before any user testing."""

    async def transcribe(self, audio: bytes, language: str) -> str:
        return audio.decode("utf-8", errors="ignore").strip()


# TODO(prod): implement GoogleSTT / AzureSTT / AfricasTalkingSTT.
# Verify per-language coverage (zu, xh, af, st, sw) before committing to a vendor.
