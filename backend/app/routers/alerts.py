"""Alert endpoints: history log, manual dispatch, and WebSocket stream."""
from __future__ import annotations

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from ..audit import audit
from ..auth.scope import district_allowed, visible_bank, visible_state
from ..auth.security import Role, get_current_user, require_roles
from ..config import settings
from ..db import SessionLocal, get_db
from ..models import Alert, User
from ..schemas import DispatchRequest
from ..alerts.dispatch import channel_capabilities, dispatch_alert
from ..alerts.ws import manager

router = APIRouter(tags=["alerts"])


def _scope_alerts(q, user: User):
    state = visible_state(user)
    bank = visible_bank(user)
    if state:
        q = q.filter((Alert.state == state) | (Alert.state.is_(None)))
    if bank:
        q = q.filter(Alert.bank_name == bank)
    return q


@router.get("/alerts")
def list_alerts(db: Session = Depends(get_db), user: User = Depends(get_current_user),
                limit: int = 100):
    q = _scope_alerts(db.query(Alert), user).order_by(Alert.created_at.desc()).limit(limit)
    rows = q.all()
    audit(db, user, "list_alerts", f"count={len(rows)}")
    return {
        "items": [
            {
                "id": a.id,
                "created_at": a.created_at.strftime("%Y-%m-%d %H:%M:%S") if a.created_at else None,
                "severity": a.severity,
                "title": a.title,
                "message": a.message,
                "district": a.district,
                "state": a.state,
                "bank_name": a.bank_name,
                "complaint_id": a.complaint_id,
                "risk_score": a.risk_score,
                "channels": a.channels.split(",") if a.channels else [],
                "status": a.status,
            }
            for a in rows
        ]
    }


@router.get("/alerts/capabilities")
def alert_capabilities(user: User = Depends(get_current_user)):
    return channel_capabilities()


@router.post("/alerts/dispatch")
async def dispatch(body: DispatchRequest, db: Session = Depends(get_db),
                   user: User = Depends(require_roles(Role.I4C_ADMIN, Role.STATE_LEA))):
    """Manual 'Dispatch Team' action — creates an audit-logged alert + WS push."""
    if body.district and not district_allowed(body.district, user):
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="District is outside your jurisdiction")
    title = f"{body.severity} manual dispatch"
    if body.district:
        title += f": {body.district}"
    message = body.message or f"Field action dispatched by {user.full_name} ({user.role})."
    alert, deduped = dispatch_alert(
        db,
        severity=body.severity,
        title=title,
        message=message,
        district=body.district,
        state=visible_state(user),
        bank_name=visible_bank(user),
        complaint_id=body.complaint_id,
        channels=body.channels,
        status="dispatched",
    )
    audit(db, user, "dispatch_alert",
          f"district={body.district} complaint={body.complaint_id} deduped={deduped}")
    if alert and not deduped:
        await manager.broadcast({
            "type": "alert",
            "severity": alert.severity,
            "title": alert.title,
            "district": alert.district,
            "state": alert.state,
            "bank_name": alert.bank_name,
        })
    return {"dispatched": bool(alert), "deduped": deduped,
            "alert_id": alert.id if alert else None}


@router.websocket("/ws/alerts")
async def alerts_ws(ws: WebSocket):
    token = ws.query_params.get("token")
    db = SessionLocal()
    try:
        payload = jwt.decode(token or "", settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("kind") != "access":
            raise JWTError("invalid token kind")
        user = db.query(User).filter(User.username == payload.get("sub"), User.is_active.is_(True)).first()
        if not user:
            raise JWTError("user not found")
    except JWTError:
        db.close()
        await ws.close(code=1008)
        return
    db.close()
    await manager.connect(ws, state=visible_state(user), bank=visible_bank(user))
    try:
        while True:
            await ws.receive_text()  # keepalive; server pushes on dispatch
    except WebSocketDisconnect:
        await manager.disconnect(ws)
