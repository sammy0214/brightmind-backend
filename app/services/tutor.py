"""Tutor LLM stage: Claude with a 'guided thinking' system prompt."""
from typing import Protocol

from anthropic import AsyncAnthropic

from app.config import get_settings

LANG_NAMES = {
    "en": "English", "zu": "isiZulu", "xh": "isiXhosa",
    "af": "Afrikaans", "st": "Sesotho", "sw": "Kiswahili",
}

HINT_RULES = {
    1: "Hint level 1: give NO answer. Ask one guiding question or point to the relevant idea.",
    2: "Hint level 2: give a stronger nudge, e.g. the first step or a similar worked example, "
       "but do not give the final answer.",
    3: "Hint level 3: walk through the method step by step, still letting the child do the "
       "final calculation or conclusion.",
}

SYSTEM_TEMPLATE = """You are BrightMind, a warm, patient voice tutor for a child in grade {grade}.
Subject: {subject}. Reply in {language}.

Rules:
- Guided thinking mode: ask questions back instead of handing over answers.
- {hint_rule}
- Keep replies under 60 words, in simple, spoken-friendly language (no lists, no markdown).
- Stay strictly within school curriculum topics for this subject and grade.
- Never ask for or repeat personal information (full name, address, phone, school, location).
- Never include links. If asked about anything off-topic or unsafe, kindly steer back to the lesson.
- Be encouraging. Praise effort, not just correct answers."""


class Tutor(Protocol):
    async def reply(
        self, *, transcript: str, history: list[tuple[str, str]], language: str,
        grade: int, subject: str, hint_level: int,
    ) -> str: ...


def build_system(language: str, grade: int, subject: str, hint_level: int) -> str:
    return SYSTEM_TEMPLATE.format(
        grade=grade, subject=subject, language=LANG_NAMES.get(language, "English"),
        hint_rule=HINT_RULES.get(hint_level, HINT_RULES[1]),
    )


class ClaudeTutor:
    def __init__(self):
        s = get_settings()
        self.client = AsyncAnthropic(api_key=s.anthropic_api_key)
        self.model = s.anthropic_model

    async def reply(self, *, transcript, history, language, grade, subject, hint_level) -> str:
        messages: list[dict] = []
        for child_said, tutor_said in history[-6:]:  # short window: cost + privacy
            messages += [
                {"role": "user", "content": child_said},
                {"role": "assistant", "content": tutor_said},
            ]
        messages.append({"role": "user", "content": transcript})
        resp = await self.client.messages.create(
            model=self.model,
            max_tokens=300,
            system=build_system(language, grade, subject, hint_level),
            messages=messages,
        )
        return "".join(b.text for b in resp.content if b.type == "text").strip()


class DevTutor:
    """Offline stand-in so the API runs without an API key."""

    async def reply(self, *, transcript, history, language, grade, subject, hint_level) -> str:
        return f"Good question! What do you already know about that in {subject}? Try telling me."
