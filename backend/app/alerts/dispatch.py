"""Persistent de-duplication and configurable multi-channel alert delivery."""
from __future__ import annotations

import json
import logging
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from urllib.request import Request, urlopen

from sqlalchemy.orm import Session

from ..config import settings
from ..models import Alert

logger = logging.getLogger("vizhi.alerts")

SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def severity_for(p_high: float) -> str:
    if p_high >= 0.75:
        return "CRITICAL"
    if p_high >= 0.5:
        return "HIGH"
    if p_high >= 0.3:
        return "MEDIUM"
    return "LOW"


def _dedup_key(
    district: str | None,
    complaint_id: str | None,
    severity: str,
    bank_name: str | None,
) -> str:
    return f"{severity}:{district or '-'}:{complaint_id or '-'}:{bank_name or '-'}"


def _redis_client():
    if not settings.redis_url:
        return None
    try:
        import redis

        return redis.Redis.from_url(settings.redis_url, socket_timeout=1)
    except Exception:
        return None


def _recently_sent(db: Session, key: str) -> bool:
    client = _redis_client()
    if client is not None:
        try:
            return bool(client.get(f"vizhi:alert:{key}"))
        except Exception as exc:
            logger.warning("Redis unavailable; using database de-duplication: %s", exc)
    cutoff = datetime.utcnow() - timedelta(minutes=settings.alert_dedup_window_minutes)
    return db.query(Alert).filter(
        Alert.dedup_key == key,
        Alert.created_at >= cutoff,
    ).first() is not None


def channel_capabilities() -> dict[str, bool]:
    """Tell the UI which providers are configured without exposing credentials."""
    return {
        "in_app": True,
        "email": bool(settings.smtp_host and settings.alert_email_to),
        "sms": bool(settings.sms_webhook_url),
        "api": bool(settings.alert_webhook_url),
    }


def _post_json(url: str, alert: Alert) -> None:
    payload = json.dumps({
        "alert_id": alert.id,
        "severity": alert.severity,
        "title": alert.title,
        "message": alert.message,
        "district": alert.district,
        "state": alert.state,
        "bank_name": alert.bank_name,
        "complaint_id": alert.complaint_id,
    }).encode("utf-8")
    request = Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=8):
        pass


def _deliver_channel(channel: str, alert: Alert) -> bool:
    try:
        if channel == "in_app":
            return True
        if channel == "email" and settings.smtp_host and settings.alert_email_to:
            message = EmailMessage()
            message["Subject"] = f"[VIZHI {alert.severity}] {alert.title}"
            message["From"] = settings.alert_email_from or settings.smtp_user
            message["To"] = settings.alert_email_to
            message.set_content(alert.message)
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
                if settings.smtp_use_tls:
                    smtp.starttls()
                if settings.smtp_user:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(message)
            return True
        if channel == "sms" and settings.sms_webhook_url:
            _post_json(settings.sms_webhook_url, alert)
            return True
        if channel == "api" and settings.alert_webhook_url:
            _post_json(settings.alert_webhook_url, alert)
            return True
    except Exception as exc:  # delivery failure must not lose the in-app alert
        logger.warning("%s delivery failed for alert %s: %s", channel, alert.id, exc)
    return False


def dispatch_alert(
    db: Session,
    *,
    severity: str,
    title: str,
    message: str,
    district: str | None = None,
    state: str | None = None,
    bank_name: str | None = None,
    complaint_id: str | None = None,
    risk_score: float | None = None,
    channels: list[str] | None = None,
    status: str = "raised",
) -> tuple[Alert | None, bool]:
    """Persist an alert, deliver configured channels, and return (alert, deduped)."""
    channels = channels or ["in_app"]
    key = _dedup_key(district, complaint_id, severity, bank_name)
    if _recently_sent(db, key):
        return None, True

    alert = Alert(
        severity=severity,
        title=title,
        message=message,
        district=district,
        state=state,
        bank_name=bank_name,
        complaint_id=complaint_id,
        risk_score=risk_score,
        channels="",
        status=status,
        dedup_key=key,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    delivered = [channel for channel in channels if _deliver_channel(channel, alert)]
    alert.channels = ",".join(delivered)
    db.commit()
    db.refresh(alert)
    client = _redis_client()
    if client is not None:
        try:
            client.setex(
                f"vizhi:alert:{key}",
                settings.alert_dedup_window_minutes * 60,
                str(alert.id),
            )
        except Exception as exc:
            logger.warning("Unable to persist Redis de-duplication key: %s", exc)
    return alert, False


def scan_and_raise(db: Session, predictions: list[dict]) -> list[Alert]:
    """Auto-raise alerts for high-risk predictions."""
    raised: list[Alert] = []
    for prediction in predictions:
        severity = severity_for(prediction["p_high"])
        if severity not in ("HIGH", "CRITICAL"):
            continue
        for bank_name in prediction.get("banks_involved", []) or [None]:
            alert, deduped = dispatch_alert(
                db,
                severity=severity,
                title=f"{severity} risk forecast: {prediction['district']}",
                message=(
                    f"Predicted {prediction['risk_level']} risk in {prediction['district']}, "
                    f"{prediction['state']} (P(HIGH)={prediction['p_high']}). Likely cash-out: "
                    + ", ".join(
                        item["withdrawal_district"]
                        for item in prediction["likely_cashout_districts"]
                    )
                ),
                district=prediction["district"],
                state=prediction["state"],
                bank_name=bank_name,
                risk_score=prediction["p_high"],
                channels=["in_app"],
            )
            if alert and not deduped:
                raised.append(alert)
    return raised
