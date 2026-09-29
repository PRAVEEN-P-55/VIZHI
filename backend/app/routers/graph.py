"""Fraud network graph endpoint (nodes/edges + detected syndicates)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..audit import audit
from ..auth.security import require_roles, Role
from ..auth.scope import visible_state
from ..db import get_db
from ..models import User

router = APIRouter(tags=["graph"])


@router.get("/graph")
def graph(db: Session = Depends(get_db),
          user: User = Depends(require_roles(Role.I4C_ADMIN, Role.STATE_LEA))):
    """Fraud syndicate network. Restricted to LEA roles (cross-bank linkage)."""
    from ..ml.graph import build_graph

    result = build_graph(state=visible_state(user))
    audit(db, user, "graph", "")
    return result
