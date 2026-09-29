"""Audit logging helper — every sensitive access is recorded for traceability."""
from __future__ import annotations

from sqlalchemy.orm import Session

from .models import AuditLog, User


def audit(db: Session, user: User | None, action: str, detail: str = "") -> None:
    """Record an audit entry. Never raises — auditing must not break the request."""
    try:
        db.add(AuditLog(
            username=getattr(user, "username", None),
            role=getattr(user, "role", None),
            action=action,
            detail=detail[:2000],
        ))
        db.commit()
    except Exception:
        db.rollback()
