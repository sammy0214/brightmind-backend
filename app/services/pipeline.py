"""STT -> tutor LLM -> moderation -> TTS. Each stage is a swappable service and
every stage's outcome is returned so it can be written to the audit log."""
import time
from dataclasses import dataclass, field

from app.services.moderation import SAFE_FALLBACK, Moderator
from app.services.stt import STT
from app.services.tts import TTS
from app.services.tutor import Tutor


@dataclass
class TurnResult:
    transcript: str
    reply_text: str
    reply_audio: bytes
    blocked: bool
    block_reason: str | None
    stage_log: dict = field(default_factory=dict)


class VoicePipeline:
    def __init__(self, stt: STT, tutor: Tutor, moderator: Moderator, tts: TTS):
        self.stt, self.tutor, self.moderator, self.tts = stt, tutor, moderator, tts

    async def run(
        self, *, audio: bytes | None, text: str | None, language: str, grade: int,
        subject: str, hint_level: int, history: list[tuple[str, str]],
    ) -> TurnResult:
        log: dict = {}

        t = time.perf_counter()
        transcript = text.strip() if text else await self.stt.transcribe(audio or b"", language)
        log["stt"] = {"ms": round((time.perf_counter() - t) * 1000), "chars": len(transcript)}

        t = time.perf_counter()
        raw_reply = await self.tutor.reply(
            transcript=transcript, history=history, language=language,
            grade=grade, subject=subject, hint_level=hint_level,
        )
        log["tutor"] = {"ms": round((time.perf_counter() - t) * 1000), "chars": len(raw_reply)}

        t = time.perf_counter()
        verdict = await self.moderator.check(raw_reply)
        log["moderation"] = {
            "ms": round((time.perf_counter() - t) * 1000),
            "allowed": verdict.allowed, "reason": verdict.reason,
        }
        reply = raw_reply if verdict.allowed else SAFE_FALLBACK

        t = time.perf_counter()
        audio_out = await self.tts.synthesize(reply, language)
        log["tts"] = {"ms": round((time.perf_counter() - t) * 1000), "bytes": len(audio_out)}

        return TurnResult(transcript, reply, audio_out, not verdict.allowed, verdict.reason, log)
