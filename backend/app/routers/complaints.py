"""Complaints listing endpoint — filterable, paginated, RBAC-scoped, PII-redacted."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..audit import audit
from ..auth.scope import district_allowed, redact_complaint, scope_complaints
from ..auth.security import get_current_user
from ..db import get_db
from ..models import Complaint, User
from ..schemas import ComplaintCreate

router = APIRouter(tags=["complaints"])


@router.post("/complaints", status_code=201)
def create_complaint(
    body: ComplaintCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Register a live complaint and immediately return its actionable forecast."""
    if user.role == "state_lea" and body.state != user.scope_value:
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="State is outside your jurisdiction")
    if user.role == "bank_officer" and body.reported_bank != user.scope_value:
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Bank is outside your scope")
    if not district_allowed(body.district, user):
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="District is outside your jurisdiction")

    now = body.timestamp or datetime.now(timezone.utc)
    if now.tzinfo is not None:
        now = now.astimezone(timezone.utc).replace(tzinfo=None)
    complaint_id = f"VIZHI-{now:%Y%m%d}-{uuid.uuid4().hex[:8].upper()}"
    victim_material = (
        f"{round(body.lat, 4)}|{round(body.lon, 4)}|"
        f"{body.reported_bank}|{body.victim_account_type}"
    )
    complaint = Complaint(
        complaint_id=complaint_id,
        timestamp=now,
        state=body.state,
        district=body.district,
        pin_code=body.pin_code,
        lat=body.lat,
        lon=body.lon,
        complaint_type=body.complaint_type,
        fraud_amount=body.fraud_amount,
        reported_bank=body.reported_bank,
        victim_account_type=body.victim_account_type,
        complaint_status=body.complaint_status,
        victim_key="V-" + hashlib.sha256(victim_material.encode()).hexdigest()[:12],
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    from ..ml.data import clear_cache
    from ..ml.pipeline import get_pipeline

    clear_cache()
    prediction = get_pipeline().predict_case(
        complaint_id=complaint_id,
        district=body.district,
        state=body.state,
        complaint_type=body.complaint_type,
        fraud_amount=body.fraud_amount,
        reported_bank=body.reported_bank,
        window_hrs=48,
        top_k=3,
    )
    audit(db, user, "create_complaint", f"complaint={complaint_id}")
    return {"complaint": redact_complaint(_row(complaint), user), "prediction": prediction}


def _row(c: Complaint) -> dict:
    return {
        "complaint_id": c.complaint_id,
        "timestamp": c.timestamp.strftime("%Y-%m-%d %H:%M"),
        "state": c.state,
        "district": c.district,
        "pin_code": c.pin_code,
        "lat": c.lat,
        "lon": c.lon,
        "complaint_type": c.complaint_type,
        "fraud_amount": c.fraud_amount,
        "reported_bank": c.reported_bank,
        "victim_account_type": c.victim_account_type,
        "complaint_status": c.complaint_status,
        "victim_key": c.victim_key,
    }


@router.get("/complaints")
def list_complaints(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    district: str | None = None,
    complaint_type: str | None = None,
    status: str | None = None,
    bank: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
):
    q = db.query(Complaint)
    q = scope_complaints(q, user)
    if district:
        q = q.filter(Complaint.district == district)
    if complaint_type:
        q = q.filter(Complaint.complaint_type == complaint_type)
    if status:
        q = q.filter(Complaint.complaint_status == status)
    if bank:
        q = q.filter(Complaint.reported_bank == bank)
    if search:
        q = q.filter(Complaint.complaint_id.ilike(f"%{search}%"))

    total = q.with_entities(func.count(Complaint.complaint_id)).scalar() or 0
    rows = (
        q.order_by(Complaint.timestamp.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [redact_complaint(_row(c), user) for c in rows]
    audit(db, user, "list_complaints", f"page={page} filtered_district={district}")
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
        "items": items,
    }


@router.get("/complaints/stats")
def complaint_stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Aggregates powering dashboard charts (trend, type mix, district bars)."""
    q = scope_complaints(db.query(Complaint), user)
    by_type = dict(
        q.with_entities(Complaint.complaint_type, func.count()).group_by(
            Complaint.complaint_type
        ).all()
    )
    by_district = dict(
        q.with_entities(Complaint.district, func.count())
        .group_by(Complaint.district)
        .order_by(func.count().desc())
        .limit(10)
        .all()
    )
    total = q.with_entities(func.count(Complaint.complaint_id)).scalar() or 0
    total_fraud = q.with_entities(func.coalesce(func.sum(Complaint.fraud_amount), 0.0)).scalar()
    return {
        "total_complaints": total,
        "total_fraud_amount": float(total_fraud),
        "by_type": by_type,
        "by_district": by_district,
    }
