from functools import lru_cache

from app.config import get_settings
from app.services.moderation import ChainModerator, LLMModerator, RuleBasedModerator
from app.services.pipeline import VoicePipeline
from app.services.storage import LocalStorage, Storage
from app.services.stt import DevSTT
from app.services.tts import DevTTS
from app.services.tutor import ClaudeTutor, DevTutor


@lru_cache
def get_pipeline() -> VoicePipeline:
    s = get_settings()
    if s.anthropic_api_key:
        tutor = ClaudeTutor()
        moderator = (
            ChainModerator(RuleBasedModerator(), LLMModerator())
            if s.use_llm_moderation else RuleBasedModerator()
        )
    else:
        tutor, moderator = DevTutor(), RuleBasedModerator()
    return VoicePipeline(DevSTT(), tutor, moderator, DevTTS())


@lru_cache
def get_storage() -> Storage:
    return LocalStorage()
