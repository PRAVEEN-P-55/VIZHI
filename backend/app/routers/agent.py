"""AI Intelligence Agent endpoint (RBAC-redacted context, audit-logged)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..agent.intelligence import answer_query, build_brief
from ..audit import audit
from ..auth.scope import district_allowed, visible_bank, visible_state
from ..auth.security import get_current_user
from ..db import get_db
from ..ml.pipeline import get_pipeline
from ..models import Complaint, User
from ..schemas import AgentQuery

router = APIRouter(tags=["agent"])


@router.post("/agent/query")
def agent_query(body: AgentQuery, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    pipe = get_pipeline()
    district = body.district
    if body.complaint_id:
        complaint = db.query(Complaint).filter(
            Complaint.complaint_id == body.complaint_id
        ).first()
        if not complaint:
            return {"answer": "data insufficient — complaint not found", "mode": "denied"}
        if not district_allowed(complaint.district, user):
            return {"answer": "data insufficient — complaint outside your jurisdiction",
                    "mode": "denied"}
        if user.role == "bank_officer" and complaint.reported_bank != user.scope_value:
            return {"answer": "data insufficient — complaint outside your bank scope",
                    "mode": "denied"}
        district = complaint.district
    # Enforce jurisdiction before the agent sees any district context.
    state = visible_state(user)
    if district and state:
        detail = pipe.explain_district(district)
        if detail and detail["state"] != state:
            return {"answer": "data insufficient — district outside your jurisdiction",
                    "mode": "denied"}
    if district and not district_allowed(district, user):
        return {"answer": "data insufficient — district outside your jurisdiction",
                "mode": "denied"}
    result = answer_query(
        pipe,
        body.query,
        district=district,
        complaint_id=body.complaint_id,
        allowed_state=visible_state(user),
        allowed_bank=visible_bank(user),
    )
    audit(db, user, "agent_query",
          f"district={result.get('focus_district')} mode={result.get('mode')} q={body.query[:120]}")
    return result


@router.get("/agent/brief/{district}")
def agent_brief(district: str, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    """Structured intelligence brief for a district (drives PDF export client-side)."""
    pipe = get_pipeline()
    state = visible_state(user)
    detail = pipe.explain_district(district)
    if detail and state and detail["state"] != state:
        return {"error": "outside your jurisdiction"}
    if detail and user.role == "bank_officer":
        pred = next((p for p in pipe.get_predictions()["predictions"]
                     if p["district"] == district), None)
        if not pred or user.scope_value not in pred.get("banks_involved", []):
            return {"error": "outside your bank scope"}
    brief = build_brief(pipe, district)
    audit(db, user, "agent_brief", district)
    return brief
