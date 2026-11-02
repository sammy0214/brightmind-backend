from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.deps import Principal, require_parent
from app.models import Child, ConsentRecord
from app.schemas import ChildIn, ChildOut, TokenOut
from app.security import create_token

router = APIRouter(prefix="/children", tags=["children"])


def _out(c: Child) -> ChildOut:
    return ChildOut(id=c.id, display_name=c.display_name, birth_year=c.birth_year,
                    grade=c.grade, language=c.language)


@router.post("", response_model=ChildOut, status_code=201)
async def add_child(body: ChildIn, p: Principal = Depends(require_parent),
                    db: AsyncSession = Depends(get_db)):
    child = Child(family_id=p.family_id, **body.model_dump())
    db.add(child)
    await db.flush()
    db.add(ConsentRecord(family_id=p.family_id, child_id=child.id, action="child_added",
                         policy_version=get_settings().consent_policy_version))
    await db.commit()
    return _out(child)


@router.get("", response_model=list[ChildOut])
async def list_children(p: Principal = Depends(require_parent),
                        db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Child).where(Child.family_id == p.family_id))).scalars()
    return [_out(c) for c in rows]


@router.post("/{child_id}/device-token", response_model=TokenOut)
async def issue_device_token(child_id: str, p: Principal = Depends(require_parent),
                             db: AsyncSession = Depends(get_db)):
    """Parent authorises a child's device. The child never has a password."""
    child = await db.get(Child, child_id)
    if child is None or child.family_id != p.family_id:
        raise HTTPException(404, "Child not found")
    token = create_token(family_id=p.family_id, role="child", child_id=child.id,
                         minutes=get_settings().child_token_minutes)
    return TokenOut(access_token=token)
