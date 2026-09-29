"""Innovative-feature endpoints: DNA fingerprinting, mule migration flow,
Golden Hour tracker, and re-victimization loop detection."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..audit import audit
from ..auth.scope import visible_bank, visible_state
from ..auth.security import Role, get_current_user, require_roles
from ..db import get_db
from ..ml.data import load_all
from ..models import User

router = APIRouter(tags=["features"])


@router.get("/dna")
def dna(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Complaint DNA fingerprint clusters (organized-ring detection)."""
    from ..ml.dna import compute_dna

    result = compute_dna(state=visible_state(user), bank=visible_bank(user))
    audit(db, user, "dna", "")
    return result


@router.get("/golden-hour")
def golden_hour(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from ..ml.golden_hour import golden_hour_active

    result = golden_hour_active(state=visible_state(user), bank=visible_bank(user))
    audit(db, user, "golden_hour", f"active={len(result['items'])}")
    return result


@router.get("/revictimization")
def revictimization(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from ..ml.golden_hour import revictimization as compute_revictimization

    result = compute_revictimization(state=visible_state(user), bank=visible_bank(user))
    audit(db, user, "revictimization", "")
    return result


@router.get("/mule-flow")
def mule_flow(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.I4C_ADMIN, Role.STATE_LEA)),
):
    """Mule-account migration: origin (complaint) state -> mule registration state.

    Returns Sankey-ready nodes/links showing where laundered money flows.
    """
    data = load_all()
    complaint_rows = data["complaints"]
    state = visible_state(user)
    if state:
        complaint_rows = complaint_rows[complaint_rows["state"] == state]
    complaints = complaint_rows.set_index("complaint_id")["state"]
    mules = data["mules"]

    flows: dict[tuple[str, str], dict] = {}
    for m in mules.itertuples():
        try:
            links = json.loads(m.linked_complaint_ids)
        except Exception:
            links = []
        for cid in links:
            origin = complaints.get(cid)
            if not origin:
                continue
            key = (f"origin:{origin}", f"mule:{m.state_registered}")
            f = flows.setdefault(key, {"count": 0, "amount": 0.0})
            f["count"] += 1
            f["amount"] += float(m.total_amount_received) / max(len(links), 1)

    nodes = sorted({n for k in flows for n in k})
    links = [
        {"source": s, "target": t, "value": v["count"],
         "amount": round(v["amount"], 2)}
        for (s, t), v in flows.items()
    ]
    links.sort(key=lambda x: x["value"], reverse=True)
    audit(db, user, "mule_flow", f"links={len(links)}")
    return {"nodes": [{"id": n, "label": n.split(':', 1)[1]} for n in nodes],
            "links": links[:60]}
