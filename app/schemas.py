from datetime import datetime

from pydantic import BaseModel, Field

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
LANGUAGES = "^(en|zu|xh|af|st|sw)$"  # English, isiZulu, isiXhosa, Afrikaans, Sesotho, Kiswahili


class RegisterIn(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN)
    password: str = Field(min_length=10)
    region: str
    consent_given: bool
    consent_policy_version: str


class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ChildIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=60)
    birth_year: int = Field(ge=2005, le=2030)
    grade: int = Field(ge=1, le=12)
    language: str = Field(default="en", pattern=LANGUAGES)


class ChildOut(ChildIn):
    id: str


class SessionIn(BaseModel):
    child_id: str | None = None  # required for parents, ignored for child tokens
    subject: str = Field(min_length=1, max_length=60)
    language: str | None = Field(default=None, pattern=LANGUAGES)


class SessionOut(BaseModel):
    id: str
    child_id: str
    subject: str
    language: str
    started_at: datetime


class TurnOut(BaseModel):
    id: str
    transcript: str
    reply_text: str
    reply_audio_b64: str
    hint_level: int
    moderation_blocked: bool


class SummaryOut(BaseModel):
    child_id: str
    days: int
    sessions: int
    minutes: float
    turns: int
    independence_score: float | None  # share of help requests where the child tried first
