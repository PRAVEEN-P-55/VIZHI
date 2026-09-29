"""Human feedback loop for intervention, blocking, and recovery outcomes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..audit import audit
from ..auth.scope import district_allowed
from ..auth.security import get_current_user
from ..db import get_db
from ..models import Complaint, InterventionOutcome, User
from ..schemas import OutcomeCreate

router = APIRouter(tags=["outcomes"])


def _scoped_complaint(db: Session, complaint_id: str, user: User) -> Complaint:
    complaint = db.query(Complaint).filter(Complaint.complaint_id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    if not district_allowed(complaint.district, user):
        raise HTTPException(status_code=403, detail="Outside your jurisdiction")
    if user.role == "bank_officer" and complaint.reported_bank != user.scope_value:
        raise HTTPException(status_code=403, detail="Outside your bank scope")
    return complaint


def _row(item: InterventionOutcome) -> dict:
    return {
        "id": item.id,
        "complaint_id": item.complaint_id,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "recorded_by": item.recorded_by,
        "action": item.action,
        "outcome": item.outcome,
        "amount_blocked": item.amount_blocked,
        "amount_recovered": item.amount_recovered,
        "notes": item.notes,
    }


@router.post("/complaints/{complaint_id}/outcomes", status_code=201)
def record_outcome(
    complaint_id: str,
    body: OutcomeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _scoped_complaint(db, complaint_id, user)
    item = InterventionOutcome(
        complaint_id=complaint_id,
        recorded_by=user.username,
        action=body.action.strip(),
        outcome=body.outcome,
        amount_blocked=body.amount_blocked,
        amount_recovered=body.amount_recovered,
        notes=body.notes.strip(),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    audit(db, user, "record_outcome", f"complaint={complaint_id} outcome={body.outcome}")
    return _row(item)


@router.get("/complaints/{complaint_id}/outcomes")
def list_outcomes(
    complaint_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _scoped_complaint(db, complaint_id, user)
    items = db.query(InterventionOutcome).filter(
        InterventionOutcome.complaint_id == complaint_id
    ).order_by(InterventionOutcome.created_at.desc()).all()
    audit(db, user, "list_outcomes", f"complaint={complaint_id}")
    return {"items": [_row(item) for item in items]}
