"""CSV ingestion pipeline.

Loads the five user-provided CSVs from `Datasets/`, validates them against the
Section-3 data contract, performs light cleaning, and writes to the database.
Idempotent: existing rows for a table are cleared before reload.

No dataset content is fabricated here — this only consumes what the user drops in.
"""
from __future__ import annotations

import hashlib
import json

import pandas as pd
from sqlalchemy import delete
from sqlalchemy.orm import Session

from .config import DATASETS_DIR
from .db import SessionLocal, init_db
from .models import (
    AtmLocation,
    Complaint,
    DistrictRiskLabel,
    InterventionOutcome,
    MuleAccount,
    Withdrawal,
)

# Required columns per the data contract (Section 3).
CONTRACTS: dict[str, list[str]] = {
    "complaints": [
        "complaint_id", "timestamp", "state", "district", "pin_code", "lat", "lon",
        "complaint_type", "fraud_amount", "reported_bank", "victim_account_type",
        "complaint_status",
    ],
    "withdrawals": [
        "withdrawal_id", "linked_complaint_id", "withdrawal_timestamp", "withdrawal_lat",
        "withdrawal_lon", "withdrawal_district", "withdrawal_pin_code", "amount_withdrawn",
        "atm_or_branch", "bank_name", "time_since_complaint_hrs",
    ],
    "atm_locations": [
        "atm_id", "bank_name", "district", "pin_code", "lat", "lon", "atm_type",
        "near_landmark",
    ],
    "mule_accounts": [
        "mule_account_id", "linked_complaint_ids", "bank_name", "account_type",
        "state_registered", "total_amount_received", "no_of_transactions", "flagged",
    ],
    "district_risk_labels": [
        "district", "state", "week_start", "complaint_count", "total_fraud_amount",
        "withdrawal_count", "risk_level",
    ],
}


class IngestError(RuntimeError):
    """Raised when a CSV violates the data contract."""


def _read_csv(name: str) -> pd.DataFrame:
    path = DATASETS_DIR / f"{name}.csv"
    if not path.exists():
        raise IngestError(f"Missing dataset: {path}")
    df = pd.read_csv(path)
    missing = [c for c in CONTRACTS[name] if c not in df.columns]
    if missing:
        raise IngestError(f"{name}.csv missing required columns: {missing}")
    return df


def _victim_key(row: pd.Series) -> str:
    """Deterministic pseudonymous victim id.

    The dataset has no explicit victim identifier, so we approximate one from
    stable attributes to enable re-victimization loop detection without exposing
    PII. This is a heuristic grouping key, not a real identity.
    """
    raw = (
        f"{round(float(row['lat']), 4)}|{round(float(row['lon']), 4)}"
        f"|{row['reported_bank']}|{row['victim_account_type']}"
    )
    return "V-" + hashlib.sha1(raw.encode()).hexdigest()[:10]


def _to_records(df: pd.DataFrame) -> list[dict]:
    return df.to_dict(orient="records")


def ingest_all(verbose: bool = True) -> dict[str, int]:
    """Load all five CSVs into the database. Returns row counts per table."""
    init_db()
    counts: dict[str, int] = {}
    db: Session = SessionLocal()
    try:
        # Clear dependent rows before parents so PostgreSQL foreign keys remain valid.
        db.execute(delete(InterventionOutcome))
        db.execute(delete(Withdrawal))
        # ---- complaints ----
        c = _read_csv("complaints")
        c["timestamp"] = pd.to_datetime(c["timestamp"], errors="coerce")
        c = c.dropna(subset=["timestamp"])
        c["pin_code"] = c["pin_code"].astype(str).str.split(".").str[0]
        c["fraud_amount"] = pd.to_numeric(c["fraud_amount"], errors="coerce").fillna(0.0)
        c["victim_key"] = c.apply(_victim_key, axis=1)
        db.execute(delete(Complaint))
        db.bulk_insert_mappings(Complaint, _to_records(c[[
            "complaint_id", "timestamp", "state", "district", "pin_code", "lat", "lon",
            "complaint_type", "fraud_amount", "reported_bank", "victim_account_type",
            "complaint_status", "victim_key",
        ]]))
        counts["complaints"] = len(c)

        # ---- withdrawals ----
        w = _read_csv("withdrawals")
        w["withdrawal_timestamp"] = pd.to_datetime(
            w["withdrawal_timestamp"], errors="coerce"
        )
        w = w.dropna(subset=["withdrawal_timestamp"])
        w["withdrawal_pin_code"] = w["withdrawal_pin_code"].astype(str).str.split(".").str[0]
        db.execute(delete(Withdrawal))
        db.bulk_insert_mappings(Withdrawal, _to_records(w[CONTRACTS["withdrawals"]]))
        counts["withdrawals"] = len(w)

        # ---- atm_locations ----
        a = _read_csv("atm_locations")
        a["pin_code"] = a["pin_code"].astype(str).str.split(".").str[0]
        db.execute(delete(AtmLocation))
        db.bulk_insert_mappings(AtmLocation, _to_records(a[CONTRACTS["atm_locations"]]))
        counts["atm_locations"] = len(a)

        # ---- mule_accounts ----
        m = _read_csv("mule_accounts")

        def _norm_links(v: object) -> str:
            if isinstance(v, str):
                try:
                    return json.dumps(json.loads(v))
                except Exception:
                    return json.dumps([s.strip() for s in v.strip("[]").split(",") if s.strip()])
            return json.dumps([])

        m["linked_complaint_ids"] = m["linked_complaint_ids"].apply(_norm_links)
        m["flagged"] = m["flagged"].astype(str).str.lower().isin(["true", "1", "yes"])
        m["no_of_transactions"] = pd.to_numeric(
            m["no_of_transactions"], errors="coerce"
        ).fillna(0).astype(int)
        db.execute(delete(MuleAccount))
        db.bulk_insert_mappings(MuleAccount, _to_records(m[CONTRACTS["mule_accounts"]]))
        counts["mule_accounts"] = len(m)

        # ---- district_risk_labels ----
        d = _read_csv("district_risk_labels")
        d["week_start"] = pd.to_datetime(d["week_start"], errors="coerce")
        d = d.dropna(subset=["week_start"])
        d["risk_level"] = d["risk_level"].str.upper().str.strip()
        db.execute(delete(DistrictRiskLabel))
        db.bulk_insert_mappings(DistrictRiskLabel, _to_records(d[CONTRACTS["district_risk_labels"]]))
        counts["district_risk_labels"] = len(d)

        db.commit()
    finally:
        db.close()

    if verbose:
        for k, v in counts.items():
            print(f"  ingested {v:>7,} rows -> {k}")
    return counts


if __name__ == "__main__":
    ingest_all()
