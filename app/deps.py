from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Family
from app.security import decode_token

bearer = HTTPBearer(auto_error=False)


@dataclass
class Principal:
    role: str  # parent | child
    family_id: str
    child_id: str | None


async def get_principal(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> Principal:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing credentials")
    try:
        claims = decode_token(creds.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token") from None
    family = await db.get(Family, claims["family_id"])
    if family is None or not family.consent_active:
        # Revoked consent immediately disables every token for the family.
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Parental consent is not active")
    return Principal(claims["role"], claims["family_id"], claims.get("child_id"))


async def require_parent(p: Principal = Depends(get_principal)) -> Principal:
    if p.role != "parent":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Parent account required")
    return p
