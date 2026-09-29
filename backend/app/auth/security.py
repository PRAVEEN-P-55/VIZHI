"""JWT auth, password hashing, and role-based access dependencies.

Uses pbkdf2_sha256 (pure Python) for hashing to avoid native-binary issues.
Three roles gate every protected endpoint: i4c_admin, state_lea, bank_officer.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import User

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


class Role(str, Enum):
    I4C_ADMIN = "i4c_admin"
    STATE_LEA = "state_lea"
    BANK_OFFICER = "bank_officer"


def hash_password(pw: str) -> str:
    return pwd_context.hash(pw)


def verify_password(pw: str, hashed: str) -> bool:
    return pwd_context.verify(pw, hashed)


def _create_token(sub: str, role: str, scope_value: str, kind: str, expires: timedelta) -> str:
    payload = {
        "sub": sub,
        "role": role,
        "scope_value": scope_value,
        "kind": kind,
        "exp": datetime.now(timezone.utc) + expires,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(user: User) -> str:
    return _create_token(
        user.username, user.role, user.scope_value, "access",
        timedelta(minutes=settings.access_token_minutes),
    )


def create_refresh_token(user: User) -> str:
    return _create_token(
        user.username, user.role, user.scope_value, "refresh",
        timedelta(days=settings.refresh_token_days),
    )


def authenticate(db: Session, username: str, password: str) -> User | None:
    user = db.query(User).filter(User.username == username, User.is_active.is_(True)).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def get_current_user(
    token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise cred_exc
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("kind") != "access":
            raise cred_exc
        username = payload.get("sub")
    except JWTError:
        raise cred_exc
    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_active:
        raise cred_exc
    return user


def require_roles(*roles: Role):
    """Dependency factory enforcing that the caller holds one of the given roles."""
    allowed = {r.value for r in roles}

    def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' not permitted for this action",
            )
        return user

    return _dep
