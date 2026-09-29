"""Role-based data scoping and PII redaction.

Central enforcement point so every router (and the AI agent) sees only what the
caller's role permits:
- i4c_admin    : national — everything.
- state_lea    : only their state's rows.
- bank_officer : only rows involving their bank; cross-bank PII redacted.
"""
from __future__ import annotations

from typing import Iterable

from sqlalchemy.orm import Query

from ..models import Complaint, User, Withdrawal

# Fields treated as PII / sensitive for redaction to out-of-scope roles.
PII_FIELDS = ("lat", "lon", "pin_code", "victim_key")


def scope_complaints(q: Query, user: User) -> Query:
    if user.role == "state_lea":
        return q.filter(Complaint.state == user.scope_value)
    if user.role == "bank_officer":
        return q.filter(Complaint.reported_bank == user.scope_value)
    return q  # i4c_admin


def scope_withdrawals(q: Query, user: User) -> Query:
    if user.role == "bank_officer":
        return q.filter(Withdrawal.bank_name == user.scope_value)
    # state_lea has no state column on withdrawals; scope via district is handled
    # by the caller when needed. Admin sees all.
    return q


def visible_state(user: User) -> str | None:
    """The single state a caller is limited to, or None for national scope."""
    if user.role == "state_lea":
        return user.scope_value
    return None


def visible_bank(user: User) -> str | None:
    if user.role == "bank_officer":
        return user.scope_value
    return None


def redact_complaint(row: dict, user: User) -> dict:
    """Redact PII fields the caller's role is not entitled to see."""
    if user.role == "i4c_admin":
        return row
    if user.role == "bank_officer" and row.get("reported_bank") != user.scope_value:
        # should not normally happen (query is scoped) but defend in depth
        return {"complaint_id": row.get("complaint_id"), "redacted": True}
    out = dict(row)
    # state_lea and bank_officer do not need precise geo/PII for cross-cutting views
    if user.role != "i4c_admin":
        for f in ("victim_key",):
            out.pop(f, None)
    return out


def filter_predictions(preds: Iterable[dict], user: User) -> list[dict]:
    """Restrict prediction rows to the caller's jurisdiction."""
    state = visible_state(user)
    result = []
    for p in preds:
        if state and p.get("state") != state:
            continue
        if user.role == "bank_officer" and user.scope_value not in p.get("banks_involved", []):
            continue
        result.append(p)
    return result


def district_allowed(district: str, user: User) -> bool:
    """Validate a district against the caller's configured jurisdiction."""
    if user.role != "state_lea":
        return True
    from ..ml.data import load_all

    labels = load_all()["labels"]
    states = labels.loc[labels["district"] == district, "state"].dropna().unique()
    return bool(len(states) and user.scope_value in states)
