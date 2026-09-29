"""Authentication + user endpoints: login, token refresh, roles, current user."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from ..audit import audit
from ..config import settings
from ..db import get_db
from ..models import User
from ..schemas import LoginRequest, RefreshRequest, Token, UserOut
from .security import (
    authenticate,
    create_access_token,
    create_refresh_token,
    get_current_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate(db, body.username, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    audit(db, user, "login", f"role={user.role}")
    return Token(
        access_token=create_access_token(user),
        refresh_token=create_refresh_token(user),
        role=user.role,
        scope_value=user.scope_value,
        full_name=user.full_name,
    )


@router.post("/refresh", response_model=Token)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(
            body.refresh_token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        if payload.get("kind") != "refresh":
            raise HTTPException(status_code=401, detail="Not a refresh token")
        user = db.query(User).filter(User.username == payload.get("sub")).first()
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")
    return Token(
        access_token=create_access_token(user),
        refresh_token=create_refresh_token(user),
        role=user.role,
        scope_value=user.scope_value,
        full_name=user.full_name,
    )


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut(
        username=user.username, full_name=user.full_name,
        role=user.role, scope_value=user.scope_value,
    )


@router.get("/roles")
def roles(user: User = Depends(get_current_user)):
    """Expose role catalogue (admin sees all; others see their own)."""
    catalogue = {
        "i4c_admin": "National visibility, all districts and alerts, user management.",
        "state_lea": "Scoped to their state/jurisdiction.",
        "bank_officer": "Scoped to their bank's complaints/withdrawals only.",
    }
    if user.role != "i4c_admin":
        return {user.role: catalogue[user.role]}
    return catalogue
