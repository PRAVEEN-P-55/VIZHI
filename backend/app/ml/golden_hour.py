"""Golden Hour tracking and re-victimization detection.

Golden Hour: most cash-outs happen 6-18h after a complaint is filed. This surfaces
complaints currently inside that critical window for urgency-based prioritization.

Re-victimization: citizens (proxied by `victim_key`) with repeat complaints are ~3x
more likely to be re-targeted; we flag them for a vulnerable-citizen alert.
"""
from __future__ import annotations

import pandas as pd

from .data import load_all

CRITICAL_START_HRS = 6
CRITICAL_END_HRS = 18


def _reference_now() -> pd.Timestamp:
    """Data is historical; anchor 'now' to the latest complaint for a live-feel demo."""
    data = load_all()
    return data["complaints"]["timestamp"].max()


def golden_hour_active(
    limit: int = 50,
    now: pd.Timestamp | None = None,
    state: str | None = None,
    bank: str | None = None,
) -> dict:
    """Complaints inside or approaching the 6-18h critical withdrawal window."""
    data = load_all()
    c = data["complaints"].copy()
    if state:
        c = c[c["state"] == state]
    if bank:
        c = c[c["reported_bank"] == bank]
    now = now or _reference_now()
    c["age_hrs"] = (now - c["timestamp"]).dt.total_seconds() / 3600.0
    # window of interest: filed within the last 24h
    live = c[(c["age_hrs"] >= 0) & (c["age_hrs"] <= 24)].copy()

    def phase(age: float) -> str:
        if age < CRITICAL_START_HRS:
            return "pre_critical"
        if age <= CRITICAL_END_HRS:
            return "critical"
        return "post_critical"

    live["phase"] = live["age_hrs"].apply(phase)
    live["hrs_to_critical_end"] = (CRITICAL_END_HRS - live["age_hrs"]).clip(lower=0)
    live = live.sort_values("age_hrs")

    items = [
        {
            "complaint_id": r.complaint_id,
            "district": r.district,
            "state": r.state,
            "complaint_type": r.complaint_type,
            "fraud_amount": float(r.fraud_amount),
            "reported_bank": r.reported_bank,
            "filed_at": r.timestamp.strftime("%Y-%m-%d %H:%M"),
            "age_hrs": round(float(r.age_hrs), 1),
            "phase": r.phase,
            "hrs_left_in_window": round(float(r.hrs_to_critical_end), 1),
        }
        for r in live.head(limit).itertuples()
    ]
    return {
        "reference_now": now.strftime("%Y-%m-%d %H:%M"),
        "critical_window_hrs": [CRITICAL_START_HRS, CRITICAL_END_HRS],
        "counts": live["phase"].value_counts().to_dict(),
        "items": items,
    }


def revictimization(
    min_complaints: int = 2,
    limit: int = 50,
    state: str | None = None,
    bank: str | None = None,
) -> dict:
    """Flag repeat victims (by pseudonymous victim_key) for vulnerable-citizen alerts."""
    data = load_all()
    c = data["complaints"]
    if state:
        c = c[c["state"] == state]
    if bank:
        c = c[c["reported_bank"] == bank]
    grp = c.groupby("victim_key").agg(
        complaints=("complaint_id", "count"),
        total_fraud=("fraud_amount", "sum"),
        districts=("district", "nunique"),
        last_seen=("timestamp", "max"),
        district=("district", lambda s: s.mode().iat[0]),
        state=("state", lambda s: s.mode().iat[0]),
    ).reset_index()
    repeat = grp[grp["complaints"] >= min_complaints].sort_values(
        "complaints", ascending=False
    )
    items = [
        {
            "victim_key": r.victim_key,
            "complaint_count": int(r.complaints),
            "total_fraud_amount": round(float(r.total_fraud), 2),
            "districts_targeted": int(r.districts),
            "district": r.district,
            "state": r.state,
            "last_complaint": r.last_seen.strftime("%Y-%m-%d"),
            "risk_multiplier": "~3x re-targeting likelihood",
        }
        for r in repeat.head(limit).itertuples()
    ]
    return {
        "repeat_victim_count": int(len(repeat)),
        "items": items,
    }
