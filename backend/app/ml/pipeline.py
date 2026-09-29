"""Training + inference pipeline.

`train_all()` fits the models and persists artifacts. `get_pipeline()` returns a
process-wide singleton the API uses for inference, with lazy caching of the
on-demand analytics (hotspots, forecast, DNA, graph).
"""
from __future__ import annotations

import json
import pickle
from functools import cached_property

import pandas as pd

from ..config import ARTIFACTS_DIR
from . import cluster, dna, forecast, golden_hour, graph, transition
from .explain import Explainer
from .features import COMPLAINT_TYPES, build_feature_table, feature_columns
from .risk_model import RiskModel, train_risk_model

RISK_MODEL_PATH = ARTIFACTS_DIR / "risk_model.pkl"
FEATURES_PATH = ARTIFACTS_DIR / "features.pkl"
TRANSITION_PATH = ARTIFACTS_DIR / "transition.pkl"
METRICS_PATH = ARTIFACTS_DIR / "metrics.json"


def train_all(k: int = 5, verbose: bool = True) -> dict:
    """Fit models and write artifacts. Returns the metrics dict."""
    if verbose:
        print("  building features + training risk model ...")
    rm = train_risk_model(k=k)
    feats = build_feature_table()
    trans = transition.build_transition()
    rm.metrics.update(transition.evaluate_transition())

    with RISK_MODEL_PATH.open("wb") as f:
        pickle.dump(rm, f)
    feats.to_pickle(FEATURES_PATH)
    with TRANSITION_PATH.open("wb") as f:
        pickle.dump(trans, f)
    METRICS_PATH.write_text(json.dumps(rm.metrics, indent=2))

    if verbose:
        print(f"  risk model [{rm.metrics['backend']}]: {rm.metrics}")
    return rm.metrics


class Pipeline:
    """Loads persisted artifacts and serves inference to the API."""

    def __init__(self):
        with RISK_MODEL_PATH.open("rb") as f:
            self.risk_model: RiskModel = pickle.load(f)
        self.features: pd.DataFrame = pd.read_pickle(FEATURES_PATH)
        with TRANSITION_PATH.open("rb") as f:
            self.transition: dict = pickle.load(f)
        self.metrics = json.loads(METRICS_PATH.read_text())
        # Destination metrics measure the actual SIH task, not only risk labels.
        try:
            self.metrics.update(transition.evaluate_transition())
        except Exception:
            pass
        self._explainer = Explainer(self.risk_model, self.features)

    # ---- risk predictions -------------------------------------------------
    def _latest_rows(self) -> pd.DataFrame:
        """Most recent week's feature row per district."""
        idx = self.features.groupby("district")["week_start"].idxmax()
        return self.features.loc[idx].reset_index(drop=True)

    def get_predictions(self, top_k: int | None = None, window_hrs: int = 48) -> dict:
        rows = self._latest_rows()
        proba = self.risk_model.predict_proba(rows)
        labels = self.risk_model.predict_label(rows)
        # Banks represented in each district; used only for bank-role scoping.
        from .data import load_all

        complaints = load_all()["complaints"]
        banks_by_district = complaints.groupby("district")["reported_bank"].apply(
            lambda values: sorted(set(values))
        ).to_dict()
        preds = []
        for i, (_, r) in enumerate(rows.iterrows()):
            p = proba[i]
            cashout = transition.predict_cashout(
                self.transition, r["district"], top=3, max_lag_hrs=window_hrs
            )
            horizon_coverage = sum(c["probability"] for c in cashout)
            p_high = float(p[2]) * (0.7 + 0.3 * min(horizon_coverage, 1.0))
            preds.append({
                "district": r["district"],
                "state": r["state"],
                "risk_level": labels[i],
                "confidence": round(float(max(p)), 3),
                "p_high": round(p_high, 3),
                "p_medium": round(float(p[1]), 3),
                "p_low": round(float(p[0]), 3),
                "window_hrs": window_hrs,
                "week_start": r["week_start"].strftime("%Y-%m-%d"),
                "likely_cashout_districts": cashout,
                "banks_involved": banks_by_district.get(r["district"], []),
                "key_indicators": self._explainer.top_indicators(r, k=5),
            })
        preds.sort(key=lambda x: x["p_high"], reverse=True)
        if top_k:
            preds = preds[:top_k]
        return {"window_hrs": window_hrs, "metrics": self.metrics, "predictions": preds}

    def explain_district(self, district: str, window_hrs: int = 48) -> dict | None:
        rows = self._latest_rows()
        match = rows[rows["district"] == district]
        if match.empty:
            return None
        r = match.iloc[0]
        proba = self.risk_model.predict_proba(match)[0]
        return {
            "district": district,
            "state": r["state"],
            "risk_level": self.risk_model.predict_label(match)[0],
            "confidence": round(float(max(proba)), 3),
            "p_high": round(float(proba[2]), 3),
            "key_indicators": self._explainer.top_indicators(r, k=6),
            "likely_cashout_districts": transition.predict_cashout(
                self.transition, district, top=5, max_lag_hrs=window_hrs
            ),
        }

    def predict_case(
        self,
        *,
        complaint_id: str | None,
        district: str,
        state: str | None,
        complaint_type: str | None,
        fraud_amount: float | None,
        reported_bank: str | None,
        window_hrs: int = 48,
        top_k: int = 3,
    ) -> dict:
        """Forecast cash-out destinations and timing for one complaint."""
        from .data import load_all

        data = load_all()
        candidates = transition.predict_cashout(
            self.transition, district, top=top_k, max_lag_hrs=window_hrs
        )
        if not candidates:
            # Cold-start fallback: rank destinations across all historical origins.
            totals: dict[str, dict] = {}
            for rows in self.transition.get("origins", {}).values():
                for row in rows:
                    if float(row.get("median_lag_hrs", 0)) > window_hrs:
                        continue
                    item = totals.setdefault(row["withdrawal_district"], {
                        "count": 0, "amount": 0.0, "lags": []
                    })
                    item["count"] += int(row.get("count", 0))
                    item["amount"] += float(row.get("total_amount", 0))
                    item["lags"].append(float(row.get("median_lag_hrs", 0)))
            total_count = sum(item["count"] for item in totals.values()) or 1
            candidates = [
                {
                    "withdrawal_district": name,
                    "probability": round(item["count"] / total_count, 4),
                    "median_lag_hrs": round(sum(item["lags"]) / len(item["lags"]), 1),
                    "count": item["count"],
                    "total_amount": round(item["amount"], 2),
                    "different_district": name != district,
                    "time_bucket": transition.time_bucket(
                        sum(item["lags"]) / len(item["lags"])
                    ),
                }
                for name, item in totals.items()
            ]
            candidates.sort(key=lambda item: item["probability"], reverse=True)
            candidates = candidates[:top_k]

        atms = data["atms"]
        destinations = []
        for rank, candidate in enumerate(candidates, 1):
            district_atms = atms[atms["district"] == candidate["withdrawal_district"]].copy()
            if reported_bank:
                district_atms["bank_match"] = (district_atms["bank_name"] == reported_bank).astype(int)
            else:
                district_atms["bank_match"] = 0
            district_atms["transport_hub"] = district_atms["near_landmark"].isin(
                ["Railway Station", "Bus Stand"]
            ).astype(int)
            district_atms = district_atms.sort_values(
                ["transport_hub", "bank_match"], ascending=False
            ).head(3)
            atm_candidates = [
                {
                    "atm_id": row.atm_id,
                    "bank_name": row.bank_name,
                    "pin_code": str(row.pin_code),
                    "lat": float(row.lat),
                    "lon": float(row.lon),
                    "atm_type": row.atm_type,
                    "near_landmark": row.near_landmark,
                }
                for row in district_atms.itertuples()
            ]
            destinations.append({
                **candidate,
                "rank": rank,
                "expected_amount": round((fraud_amount or 0) * 0.87 * candidate["probability"], 2),
                "atm_candidates": atm_candidates,
            })

        district_detail = self.explain_district(district, window_hrs=window_hrs)
        confidence = destinations[0]["probability"] if destinations else 0.0
        return {
            "complaint_id": complaint_id,
            "origin": {"district": district, "state": state},
            "complaint_type": complaint_type,
            "reported_bank": reported_bank,
            "fraud_amount": fraud_amount,
            "window_hrs": window_hrs,
            "prediction_confidence": round(float(confidence), 3),
            "destinations": destinations,
            "key_indicators": district_detail["key_indicators"] if district_detail else [],
            "model_metrics": self.metrics,
            "method": "historical origin-to-cashout transition + ATM operational ranking",
        }

    # ---- lazily-cached analytics -----------------------------------------
    @cached_property
    def hotspots(self) -> list[dict]:
        return cluster.compute_hotspots()

    @cached_property
    def forecast(self) -> dict:
        return forecast.forecast_complaints()

    @cached_property
    def dna(self) -> dict:
        return dna.compute_dna()

    @cached_property
    def graph(self) -> dict:
        return graph.build_graph()

    def golden_hour(self):
        return golden_hour.golden_hour_active()

    def revictimization(self):
        return golden_hour.revictimization()


_pipeline: Pipeline | None = None


def get_pipeline() -> Pipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = Pipeline()
    return _pipeline


def reload_pipeline() -> None:
    global _pipeline
    _pipeline = None
