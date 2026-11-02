from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.deps import Principal, require_parent
from app.models import ConsentRecord, Family
from app.schemas import LoginIn, RegisterIn, TokenOut
from app.security import create_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def _parent_token(family_id: str) -> str:
    return create_token(
        family_id=family_id, role="parent", child_id=None,
        minutes=get_settings().parent_token_minutes,
    )


@router.post("/register", response_model=TokenOut, status_code=201)
async def register(body: RegisterIn, db: AsyncSession = Depends(get_db)):
    s = get_settings()
    if not body.consent_given:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Parental consent is required")
    if body.consent_policy_version != s.consent_policy_version:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Outdated consent policy version")
    if body.region != s.region:
        # Data residency: this deployment only holds its own region's data.
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"This deployment serves region '{s.region}'. Use the endpoint for '{body.region}'.",
        )
    family = Family(email=body.email.lower(), password_hash=hash_password(body.password),
                    region=s.region)
    db.add(family)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered") from None
    db.add(ConsentRecord(family_id=family.id, action="granted",
                         policy_version=body.consent_policy_version))
    await db.commit()
    return TokenOut(access_token=_parent_token(family.id))


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, db: AsyncSession = Depends(get_db)):
    family = (await db.execute(
        select(Family).where(Family.email == body.email.lower())
    )).scalar_one_or_none()
    if family is None or not verify_password(body.password, family.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if not family.consent_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Parental consent was revoked")
    return TokenOut(access_token=_parent_token(family.id))


@router.post("/consent/revoke", status_code=204)
async def revoke_consent(p: Principal = Depends(require_parent),
                         db: AsyncSession = Depends(get_db)):
    family = await db.get(Family, p.family_id)
    family.consent_active = False
    db.add(ConsentRecord(family_id=family.id, action="revoked",
                         policy_version=get_settings().consent_policy_version))
    await db.commit()
    # TODO: enqueue background job to delete/anonymise the family's data per policy.
