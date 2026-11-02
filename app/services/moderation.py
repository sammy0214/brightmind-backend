"""Independent safety filter on tutor output. Runs regardless of what the tutor produced.
Fails CLOSED: any error or doubt means the child gets the safe fallback instead."""
import json
import re
from dataclasses import dataclass
from typing import Protocol

from anthropic import AsyncAnthropic

from app.config import get_settings

SAFE_FALLBACK = "Let's get back to our lesson. What would you like to try next?"
# TODO(localisation): add vetted fallbacks per language (zu, xh, af, st, sw) from native speakers.


@dataclass
class ModerationResult:
    allowed: bool
    reason: str | None = None


class Moderator(Protocol):
    async def check(self, text: str) -> ModerationResult: ...


BLOCK_PATTERNS = {
    "url": r"https?://|www\.|\.com\b",
    "contact_info": r"\b(phone number|whatsapp|home address|where do you live|your address)\b",
    "secrecy": r"\b(don'?t tell (your )?(mom|dad|parents?)|our secret|keep (this|it) secret)\b",
    "violence": r"\b(kill|murder|stab|shoot|weapon|gun)\b",
    "sexual": r"\b(sex|sexual|naked|porn)\b",
    "self_harm": r"\b(suicide|kill yourself|hurt yourself|self-harm)\b",
    "substances": r"\b(cocaine|heroin|vape|alcohol|beer|drugs?)\b",
    "profanity": r"\b(fuck|shit|bitch)\b",
}


class RuleBasedModerator:
    async def check(self, text: str) -> ModerationResult:
        if not text.strip():
            return ModerationResult(False, "empty_output")
        for name, pattern in BLOCK_PATTERNS.items():
            if re.search(pattern, text, re.IGNORECASE):
                return ModerationResult(False, f"rule:{name}")
        return ModerationResult(True)


class LLMModerator:
    """Second opinion from a separate Claude call with a narrow classifier prompt."""

    PROMPT = (
        "You are a child-safety classifier for an educational tutor used by children aged 6-17. "
        'Reply ONLY with JSON: {"safe": true|false, "reason": "<short>"}. '
        "Mark unsafe if the text is off-topic from schoolwork, inappropriate for children, "
        "requests personal info, includes links, encourages secrecy from parents, or gives "
        "harmful instructions."
    )

    def __init__(self):
        s = get_settings()
        self.client = AsyncAnthropic(api_key=s.anthropic_api_key)
        self.model = s.anthropic_model

    async def check(self, text: str) -> ModerationResult:
        try:
            resp = await self.client.messages.create(
                model=self.model, max_tokens=100, system=self.PROMPT,
                messages=[{"role": "user", "content": f"<text>{text}</text>"}],
            )
            raw = "".join(b.text for b in resp.content if b.type == "text")
            data = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
            return ModerationResult(bool(data["safe"]), None if data["safe"] else
                                    f"llm:{str(data.get('reason', ''))[:120]}")
        except Exception:  # fail closed
            return ModerationResult(False, "llm_moderation_error")


class ChainModerator:
    def __init__(self, *moderators: Moderator):
        self.moderators = moderators

    async def check(self, text: str) -> ModerationResult:
        for m in self.moderators:
            result = await m.check(text)
            if not result.allowed:
                return result
        return ModerationResult(True)
