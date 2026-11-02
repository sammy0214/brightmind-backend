from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import Principal, require_parent
from app.models import Child, IndependenceEvent, TutorSession, Turn
from app.schemas import SummaryOut

router = APIRouter(prefix="/dashboard", tags=["parent dashboard"])


@router.get("/children/{child_id}/summary", response_model=SummaryOut)
async def child_summary(child_id: str, days: int = Query(default=7, ge=1, le=90),
                        p: Principal = Depends(require_parent),
                        db: AsyncSession = Depends(get_db)):
    child = await db.get(Child, child_id)
    if child is None or child.family_id != p.family_id:
        raise HTTPException(404, "Child not found")
    since = datetime.now(UTC) - timedelta(days=days)

    sessions, seconds = (await db.execute(
        select(func.count(TutorSession.id),
               func.coalesce(func.sum(TutorSession.duration_seconds), 0))
        .where(TutorSession.child_id == child_id, TutorSession.started_at >= since)
    )).one()
    turns = (await db.execute(
        select(func.count(Turn.id)).join(TutorSession, Turn.session_id == TutorSession.id)
        .where(TutorSession.child_id == child_id, Turn.created_at >= since)
    )).scalar_one()
    total, tried = (await db.execute(
        select(func.count(IndependenceEvent.id),
               func.coalesce(func.sum(case((IndependenceEvent.attempted_first.is_(True), 1), else_=0)), 0))
        .where(IndependenceEvent.child_id == child_id, IndependenceEvent.created_at >= since)
    )).one()

    return SummaryOut(
        child_id=child_id, days=days, sessions=sessions, minutes=round(seconds / 60, 1),
        turns=turns, independence_score=round(tried / total, 2) if total else None,
    )
