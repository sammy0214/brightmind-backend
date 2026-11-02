"""Core tables from the architecture plan.

Design rules:
- Children have NO credentials. The parent (family) is the root of trust.
- consent_records is append-only (enforced here and should also be enforced at the DB
  level in production with REVOKE UPDATE, DELETE or a trigger).
- turns reference audio by object-storage key, never store raw audio in Postgres.
"""
import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _id() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


class ImmutableRecordError(RuntimeError):
    pass


class Family(Base):
    __tablename__ = "families"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(300))
    region: Mapped[str] = mapped_column(String(32))
    consent_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    children: Mapped[list["Child"]] = relationship(back_populates="family")


class Child(Base):
    __tablename__ = "children"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    family_id: Mapped[str] = mapped_column(ForeignKey("families.id"), index=True)
    display_name: Mapped[str] = mapped_column(String(60))  # first name / nickname only
    birth_year: Mapped[int] = mapped_column(Integer)  # year only: data minimisation
    grade: Mapped[int] = mapped_column(Integer)
    language: Mapped[str] = mapped_column(String(8), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    family: Mapped[Family] = relationship(back_populates="children")


class ConsentRecord(Base):
    __tablename__ = "consent_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    family_id: Mapped[str] = mapped_column(ForeignKey("families.id"), index=True)
    child_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(32))  # granted | revoked | child_added
    policy_version: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


@event.listens_for(ConsentRecord, "before_update")
def _block_consent_update(*_args):
    raise ImmutableRecordError("consent_records is append-only")


@event.listens_for(ConsentRecord, "before_delete")
def _block_consent_delete(*_args):
    raise ImmutableRecordError("consent_records is append-only")


class TutorSession(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    child_id: Mapped[str] = mapped_column(ForeignKey("children.id"), index=True)
    subject: Mapped[str] = mapped_column(String(60))
    language: Mapped[str] = mapped_column(String(8))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    turns: Mapped[list["Turn"]] = relationship(back_populates="session", order_by="Turn.created_at")


class Turn(Base):
    __tablename__ = "turns"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), index=True)
    transcript: Mapped[str] = mapped_column(Text)
    reply_text: Mapped[str] = mapped_column(Text)
    hint_level: Mapped[int] = mapped_column(Integer, default=1)
    moderation_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    moderation_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    audio_in_key: Mapped[str | None] = mapped_column(String(300), nullable=True)
    audio_out_key: Mapped[str | None] = mapped_column(String(300), nullable=True)
    stage_log: Mapped[dict] = mapped_column(JSON, default=dict)  # per-stage audit trail
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    session: Mapped[TutorSession] = relationship(back_populates="turns")


class IndependenceEvent(Base):
    __tablename__ = "independence_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    child_id: Mapped[str] = mapped_column(ForeignKey("children.id"), index=True)
    turn_id: Mapped[str] = mapped_column(ForeignKey("turns.id"))
    attempted_first: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
