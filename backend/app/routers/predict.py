"""Prediction + heatmap + forecast endpoints (RBAC-scoped, audit-logged)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..audit import audit
from ..auth.scope import district_allowed, filter_predictions, visible_bank, visible_state
from ..auth.security import get_current_user
from ..db import get_db
from ..ml.pipeline import get_pipeline
from ..models import Complaint, User
from ..schemas import CasePredictRequest, PredictRequest

router = APIRouter(tags=["predictions"])


@router.post("/predict")
def predict(body: PredictRequest, db: Session = Depends(get_db),
            user: User = Depends(get_current_user)):
    pipe = get_pipeline()
    result = pipe.get_predictions(top_k=None, window_hrs=body.window_hrs)
    preds = filter_predictions(result["predictions"], user)
    if body.top_k:
        preds = preds[: body.top_k]
    audit(db, user, "predict", f"window={body.window_hrs} returned={len(preds)}")
    return {
        "window_hrs": body.window_hrs,
        "metrics": result["metrics"],
        "scope": visible_state(user) or "national",
        "predictions": preds,
    }


@router.post("/predict/case")
def predict_case(body: CasePredictRequest, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    """Forecast ranked cash-out zones and time buckets for one complaint."""
    complaint = None
    if body.complaint_id:
        complaint = db.query(Complaint).filter(
            Complaint.complaint_id == body.complaint_id
        ).first()
        if not complaint:
            raise HTTPException(status_code=404, detail="Complaint not found")
        if not district_allowed(complaint.district, user):
            raise HTTPException(status_code=403, detail="Outside your jurisdiction")
        if user.role == "bank_officer" and complaint.reported_bank != user.scope_value:
            raise HTTPException(status_code=403, detail="Complaint is outside your bank scope")

    district = complaint.district if complaint else body.district
    if not district:
        raise HTTPException(status_code=422, detail="district or complaint_id is required")
    if not district_allowed(district, user):
        raise HTTPException(status_code=403, detail="Outside your jurisdiction")
    bank = complaint.reported_bank if complaint else body.reported_bank
    if user.role == "bank_officer" and bank != user.scope_value:
        raise HTTPException(status_code=403, detail="reported_bank must match your bank scope")

    pipe = get_pipeline()
    result = pipe.predict_case(
        complaint_id=complaint.complaint_id if complaint else body.complaint_id,
        district=district,
        state=complaint.state if complaint else body.state,
        complaint_type=complaint.complaint_type if complaint else body.complaint_type,
        fraud_amount=complaint.fraud_amount if complaint else body.fraud_amount,
        reported_bank=bank,
        window_hrs=body.window_hrs,
        top_k=body.top_k,
    )
    audit(db, user, "predict_case", f"complaint={body.complaint_id} district={district}")
    return result


@router.get("/predict/{district}")
def explain(district: str, db: Session = Depends(get_db),
            user: User = Depends(get_current_user)):
    pipe = get_pipeline()
    detail = pipe.explain_district(district)
    if detail is None:
        return {"error": f"no analytics for '{district}'"}
    state = visible_state(user)
    if state and detail["state"] != state:
        return {"error": "outside your jurisdiction"}
    if user.role == "bank_officer":
        pred = next((p for p in pipe.get_predictions()["predictions"]
                     if p["district"] == district), None)
        if not pred or user.scope_value not in pred.get("banks_involved", []):
            return {"error": "outside your bank scope"}
    audit(db, user, "explain_district", district)
    return detail


@router.get("/heatmap")
def heatmap(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Geospatial risk zones for the map. Districts merged with predicted risk."""
    pipe = get_pipeline()
    zones = pipe.hotspots
    preds = {p["district"]: p for p in pipe.get_predictions()["predictions"]}
    state = visible_state(user)
    bank = visible_bank(user)
    enriched = []
    for z in zones:
        pred = preds.get(z["dominant_district"])
        if state and (not pred or pred["state"] != state):
            continue
        if bank and z.get("dominant_bank") != bank:
            continue
        enriched.append({
            **z,
            "predicted_risk": pred["risk_level"] if pred else "UNKNOWN",
            "p_high": pred["p_high"] if pred else None,
        })
    audit(db, user, "heatmap", f"zones={len(enriched)}")
    return {"scope": state or "national", "zones": enriched}


@router.get("/forecast")
def forecast(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from ..ml.forecast import forecast_complaints

    audit(db, user, "forecast", "")
    return forecast_complaints(state=visible_state(user), bank=visible_bank(user))


@router.get("/map/layers")
def map_layers(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    sample: int = 700,
):
    """Sampled point layers for the map: complaints, withdrawals, ATM clusters."""
    from ..ml.data import load_all

    data = load_all()
    state = visible_state(user)
    bank = user.scope_value if user.role == "bank_officer" else None

    c = data["complaints"]
    w = data["withdrawals"]
    a = data["atms"]
    if state:
        c = c[c["state"] == state]
        districts = set(c["district"].unique())
        w = w[w["withdrawal_district"].isin(districts)]
        a = a[a["district"].isin(districts)]
    if bank:
        c = c[c["reported_bank"] == bank]
        w = w[w["bank_name"] == bank]
        a = a[a["bank_name"] == bank]

    def _sample(df, n):
        return df.sample(min(n, len(df)), random_state=1) if len(df) else df

    complaints = [
        {"lat": r.lat, "lon": r.lon, "district": r.district,
         "type": r.complaint_type, "amount": float(r.fraud_amount)}
        for r in _sample(c, sample).itertuples()
    ]
    withdrawals = [
        {"lat": r.withdrawal_lat, "lon": r.withdrawal_lon,
         "district": r.withdrawal_district, "amount": float(r.amount_withdrawn),
         "bank": r.bank_name}
        for r in _sample(w, sample).itertuples()
    ]
    atms = [
        {"lat": r.lat, "lon": r.lon, "district": r.district, "bank": r.bank_name,
         "landmark": r.near_landmark, "type": r.atm_type}
        for r in a.itertuples()
    ]
    audit(db, user, "map_layers", f"c={len(complaints)} w={len(withdrawals)}")
    return {"complaints": complaints, "withdrawals": withdrawals, "atms": atms}
