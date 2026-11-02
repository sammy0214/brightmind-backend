import base64
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import Principal, get_principal
from app.models import Child, IndependenceEvent, TutorSession, Turn
from app.schemas import SessionIn, SessionOut, TurnOut
from app.services.factory import get_pipeline, get_storage

router = APIRouter(prefix="/sessions", tags=["sessions"])
MAX_AUDIO_BYTES = 2 * 1024 * 1024


async def _child_for(p: Principal, requested_id: str | None, db: AsyncSession) -> Child:
    child_id = p.child_id if p.role == "child" else requested_id
    if not child_id:
        raise HTTPException(422, "child_id is required")
    child = await db.get(Child, child_id)
    if child is None or child.family_id != p.family_id:
        raise HTTPException(404, "Child not found")
    return child


async def _session_for(session_id: str, p: Principal, db: AsyncSession) -> TutorSession:
    sess = await db.get(TutorSession, session_id)
    if sess is None:
        raise HTTPException(404, "Session not found")
    child = await db.get(Child, sess.child_id)
    if child.family_id != p.family_id or (p.role == "child" and p.child_id != child.id):
        raise HTTPException(404, "Session not found")
    return sess


@router.post("", response_model=SessionOut, status_code=201)
async def start_session(body: SessionIn, p: Principal = Depends(get_principal),
                        db: AsyncSession = Depends(get_db)):
    child = await _child_for(p, body.child_id, db)
    sess = TutorSession(child_id=child.id, subject=body.subject,
                        language=body.language or child.language)
    db.add(sess)
    await db.commit()
    return SessionOut(id=sess.id, child_id=sess.child_id, subject=sess.subject,
                      language=sess.language, started_at=sess.started_at)


@router.post("/{session_id}/turns", response_model=TurnOut, status_code=201)
async def add_turn(
    session_id: str,
    audio: UploadFile | None = File(default=None),
    text: str | None = Form(default=None, max_length=1000),  # dev/testing shortcut
    hint_level: int = Form(default=1, ge=1, le=3),
    attempted_first: bool = Form(default=False),
    p: Principal = Depends(get_principal),
    db: AsyncSession = Depends(get_db),
):
    sess = await _session_for(session_id, p, db)
    if sess.ended_at is not None:
        raise HTTPException(409, "Session already ended")
    child = await db.get(Child, sess.child_id)

    audio_bytes = None
    if audio is not None:
        audio_bytes = await audio.read(MAX_AUDIO_BYTES + 1)
        if len(audio_bytes) > MAX_AUDIO_BYTES:
            raise HTTPException(413, "Audio clip too large")
    if not audio_bytes and not text:
        raise HTTPException(422, "Provide an audio clip or text")

    prior = (await db.execute(
        select(Turn).where(Turn.session_id == sess.id).order_by(Turn.created_at)
    )).scalars().all()
    history = [(t.transcript, t.reply_text) for t in prior]

    result = await get_pipeline().run(
        audio=audio_bytes, text=text, language=sess.language, grade=child.grade,
        subject=sess.subject, hint_level=hint_level, history=history,
    )

    turn = Turn(
        session_id=sess.id, transcript=result.transcript, reply_text=result.reply_text,
        hint_level=hint_level, moderation_blocked=result.blocked,
        moderation_reason=result.block_reason, stage_log=result.stage_log,
    )
    db.add(turn)
    await db.flush()

    storage = get_storage()
    base = f"audio/{child.id}/{turn.id}"
    if audio_bytes:
        turn.audio_in_key = await storage.put(f"{base}_in.opus", audio_bytes)
    turn.audio_out_key = await storage.put(f"{base}_out.opus", result.reply_audio)

    db.add(IndependenceEvent(child_id=child.id, turn_id=turn.id,
                             attempted_first=attempted_first))
    await db.commit()

    return TurnOut(
        id=turn.id, transcript=turn.transcript, reply_text=turn.reply_text,
        reply_audio_b64=base64.b64encode(result.reply_audio).decode(),
        hint_level=hint_level, moderation_blocked=result.blocked,
    )


@router.post("/{session_id}/end", response_model=SessionOut)
async def end_session(session_id: str, p: Principal = Depends(get_principal),
                      db: AsyncSession = Depends(get_db)):
    sess = await _session_for(session_id, p, db)
    if sess.ended_at is None:
        sess.ended_at = datetime.now(UTC)
        started = sess.started_at if sess.started_at.tzinfo else sess.started_at.replace(tzinfo=UTC)
        sess.duration_seconds = int((sess.ended_at - started).total_seconds())
        await db.commit()
    return SessionOut(id=sess.id, child_id=sess.child_id, subject=sess.subject,
                      language=sess.language, started_at=sess.started_at)
