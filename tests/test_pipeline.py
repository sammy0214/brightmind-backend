import asyncio

from app.services.moderation import SAFE_FALLBACK, RuleBasedModerator
from app.services.pipeline import VoicePipeline
from app.services.stt import DevSTT
from app.services.tts import DevTTS


class BadTutor:
    async def reply(self, **_kw):
        return "Sure! Go to https://bad.example and don't tell your parents."


def test_unsafe_tutor_output_never_reaches_child():
    pipe = VoicePipeline(DevSTT(), BadTutor(), RuleBasedModerator(), DevTTS())
    result = asyncio.run(pipe.run(
        audio=None, text="help", language="en", grade=4,
        subject="maths", hint_level=1, history=[],
    ))
    assert result.blocked
    assert result.reply_text == SAFE_FALLBACK
    assert result.reply_audio == SAFE_FALLBACK.encode()
    assert set(result.stage_log) == {"stt", "tutor", "moderation", "tts"}
