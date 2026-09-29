"""Pydantic request/response schemas for the API."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str
    scope_value: str
    full_name: str


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    username: str
    full_name: str
    role: str
    scope_value: str


class PredictRequest(BaseModel):
    window_hrs: int = Field(48, ge=6, le=72)
    top_k: int | None = Field(10, ge=1, le=50)


class CasePredictRequest(BaseModel):
    """A historical complaint ID or the minimum fields for a new case forecast."""

    complaint_id: str | None = None
    district: str | None = None
    state: str | None = None
    complaint_type: str | None = None
    fraud_amount: float | None = Field(None, gt=0)
    reported_bank: str | None = None
    reported_at: datetime | None = None
    window_hrs: int = Field(48, ge=6, le=72)
    top_k: int = Field(3, ge=1, le=10)


class ComplaintCreate(BaseModel):
    state: str
    district: str
    pin_code: str = Field(min_length=6, max_length=6)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    complaint_type: str
    fraud_amount: float = Field(gt=0)
    reported_bank: str
    victim_account_type: str = "savings"
    complaint_status: str = "open"
    timestamp: datetime | None = None

    @field_validator("state", "district", "complaint_type", "reported_bank")
    @classmethod
    def non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value


class OutcomeCreate(BaseModel):
    action: str
    outcome: str
    amount_blocked: float = Field(0, ge=0)
    amount_recovered: float = Field(0, ge=0)
    notes: str = Field("", max_length=2000)

    @field_validator("outcome")
    @classmethod
    def valid_outcome(cls, value: str) -> str:
        value = value.lower().strip()
        allowed = {"blocked", "withdrawn", "recovered", "false_positive", "pending"}
        if value not in allowed:
            raise ValueError("invalid intervention outcome")
        return value


class AgentQuery(BaseModel):
    query: str
    district: str | None = None
    complaint_id: str | None = None


class DispatchRequest(BaseModel):
    severity: str = "HIGH"
    district: str | None = None
    complaint_id: str | None = None
    message: str | None = None
    channels: list[str] = Field(default_factory=lambda: ["in_app", "sms", "email"])

    @field_validator("severity")
    @classmethod
    def valid_severity(cls, value: str) -> str:
        value = value.upper()
        if value not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
            raise ValueError("invalid severity")
        return value

    @field_validator("channels")
    @classmethod
    def valid_channels(cls, value: list[str]) -> list[str]:
        allowed = {"in_app", "dashboard", "sms", "email", "api"}
        if any(item not in allowed for item in value):
            raise ValueError("unsupported notification channel")
        normalized = ["in_app" if item == "dashboard" else item for item in value]
        return list(dict.fromkeys(normalized))
