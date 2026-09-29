"""SQLAlchemy ORM models.

Five domain tables mirror the Section-3 data contract exactly (plus optional
derived columns), and three operational tables (`users`, `alerts`, `audit_log`)
support RBAC, alerting, and audit traceability.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Complaint(Base):
    __tablename__ = "complaints"

    complaint_id: Mapped[str] = mapped_column(String, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    state: Mapped[str] = mapped_column(String, index=True)
    district: Mapped[str] = mapped_column(String, index=True)
    pin_code: Mapped[str] = mapped_column(String, index=True)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    complaint_type: Mapped[str] = mapped_column(String, index=True)
    fraud_amount: Mapped[float] = mapped_column(Float)
    reported_bank: Mapped[str] = mapped_column(String, index=True)
    victim_account_type: Mapped[str] = mapped_column(String)
    complaint_status: Mapped[str] = mapped_column(String, index=True)
    # derived: pseudonymous victim key for re-victimization detection
    victim_key: Mapped[str | None] = mapped_column(String, index=True, nullable=True)


class Withdrawal(Base):
    __tablename__ = "withdrawals"

    withdrawal_id: Mapped[str] = mapped_column(String, primary_key=True)
    linked_complaint_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("complaints.complaint_id"), index=True, nullable=True
    )
    withdrawal_timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    withdrawal_lat: Mapped[float] = mapped_column(Float)
    withdrawal_lon: Mapped[float] = mapped_column(Float)
    withdrawal_district: Mapped[str] = mapped_column(String, index=True)
    withdrawal_pin_code: Mapped[str] = mapped_column(String)
    amount_withdrawn: Mapped[float] = mapped_column(Float)
    atm_or_branch: Mapped[str] = mapped_column(String)
    bank_name: Mapped[str] = mapped_column(String, index=True)
    time_since_complaint_hrs: Mapped[float] = mapped_column(Float)


class AtmLocation(Base):
    __tablename__ = "atm_locations"

    atm_id: Mapped[str] = mapped_column(String, primary_key=True)
    bank_name: Mapped[str] = mapped_column(String, index=True)
    district: Mapped[str] = mapped_column(String, index=True)
    pin_code: Mapped[str] = mapped_column(String)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    atm_type: Mapped[str] = mapped_column(String)
    near_landmark: Mapped[str | None] = mapped_column(String, nullable=True)


class MuleAccount(Base):
    __tablename__ = "mule_accounts"

    mule_account_id: Mapped[str] = mapped_column(String, primary_key=True)
    # stored as JSON string of complaint ids
    linked_complaint_ids: Mapped[str] = mapped_column(Text)
    bank_name: Mapped[str] = mapped_column(String, index=True)
    account_type: Mapped[str] = mapped_column(String)
    state_registered: Mapped[str] = mapped_column(String, index=True)
    total_amount_received: Mapped[float] = mapped_column(Float)
    no_of_transactions: Mapped[int] = mapped_column(Integer)
    flagged: Mapped[bool] = mapped_column(Boolean, default=False)


class DistrictRiskLabel(Base):
    __tablename__ = "district_risk_labels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    district: Mapped[str] = mapped_column(String, index=True)
    state: Mapped[str] = mapped_column(String, index=True)
    week_start: Mapped[datetime] = mapped_column(DateTime, index=True)
    complaint_count: Mapped[int] = mapped_column(Integer)
    total_fraud_amount: Mapped[float] = mapped_column(Float)
    withdrawal_count: Mapped[int] = mapped_column(Integer)
    risk_level: Mapped[str] = mapped_column(String, index=True)


# --------------------------------------------------------------------------
# Operational tables: RBAC users, alerts, and audit trail
# --------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String)
    hashed_password: Mapped[str] = mapped_column(String)
    # one of: i4c_admin | state_lea | bank_officer
    role: Mapped[str] = mapped_column(String, index=True)
    # scope value: state name for state_lea, bank name for bank_officer, "" for admin
    scope_value: Mapped[str] = mapped_column(String, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True
    )
    severity: Mapped[str] = mapped_column(String, index=True)  # LOW/MEDIUM/HIGH/CRITICAL
    title: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(Text)
    district: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    state: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    bank_name: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    complaint_id: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    channels: Mapped[str] = mapped_column(String, default="")  # csv of channels used
    status: Mapped[str] = mapped_column(String, default="raised")  # raised/dispatched/closed
    dedup_key: Mapped[str | None] = mapped_column(String, index=True, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    username: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    role: Mapped[str | None] = mapped_column(String, nullable=True)
    action: Mapped[str] = mapped_column(String, index=True)
    detail: Mapped[str] = mapped_column(Text, default="")


class InterventionOutcome(Base):
    """Human-verified result used for recovery reporting and model feedback."""

    __tablename__ = "intervention_outcomes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    complaint_id: Mapped[str] = mapped_column(
        String, ForeignKey("complaints.complaint_id"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True
    )
    recorded_by: Mapped[str] = mapped_column(String, index=True)
    action: Mapped[str] = mapped_column(String)
    outcome: Mapped[str] = mapped_column(String, index=True)
    amount_blocked: Mapped[float] = mapped_column(Float, default=0.0)
    amount_recovered: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str] = mapped_column(Text, default="")
