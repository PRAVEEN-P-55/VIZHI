"""SHAP-based explainability for risk predictions.

Turns model feature attributions into plain-language "Key Indicators" that briefs
and the AI agent can cite. Falls back to model feature importances if SHAP fails.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# human-friendly phrasing for engineered feature names
FEATURE_LABELS = {
    "complaint_count": "complaint volume this week",
    "total_fraud_amount": "total fraud amount",
    "withdrawal_count": "withdrawal activity",
    "c_mean_fraud": "average fraud amount per complaint",
    "c_max_fraud": "largest single fraud",
    "c_unique_pins": "geographic spread (unique PINs)",
    "c_unique_banks": "number of banks involved",
    "c_weekend_ratio": "share of complaints on Fri-Sun",
    "w_sum_amount": "total amount withdrawn locally",
    "w_mean_lag_hrs": "avg hours from complaint to withdrawal",
    "mule_links": "linked mule-account activity",
    "complaint_count_lag1": "prior-week complaint volume",
    "withdrawal_count_lag1": "prior-week withdrawals",
    "total_fraud_amount_lag1": "prior-week fraud amount",
    "risk_lag1": "prior-week risk level",
}


def _label(col: str) -> str:
    if col.startswith("prop_"):
        return f"share of {col[5:].replace('_', ' ')} complaints"
    return FEATURE_LABELS.get(col, col)


class Explainer:
    def __init__(self, risk_model, background: pd.DataFrame):
        self.rm = risk_model
        self.cols = risk_model.columns
        self.shap_values = None
        try:
            import shap

            self._explainer = shap.TreeExplainer(risk_model.model)
            self._shap = shap
        except Exception:
            self._explainer = None
            self._shap = None
        self.background = background[self.cols]

    def top_indicators(self, row: pd.Series, k: int = 5) -> list[dict]:
        """Return the top-k features pushing this district toward higher risk."""
        X = pd.DataFrame([row[self.cols]])
        contribs: dict[str, float]
        if self._explainer is not None:
            try:
                sv = self._explainer.shap_values(X)
                # multiclass -> take HIGH class (index 2) contributions
                arr = sv[2] if isinstance(sv, list) else sv
                vals = np.asarray(arr).reshape(len(self.cols), -1)[:, 0] \
                    if np.asarray(arr).ndim == 1 else np.asarray(arr)[0]
                contribs = dict(zip(self.cols, np.asarray(vals).ravel()[: len(self.cols)]))
            except Exception:
                contribs = self._importance_fallback()
        else:
            contribs = self._importance_fallback()

        ranked = sorted(contribs.items(), key=lambda kv: abs(kv[1]), reverse=True)[:k]
        return [
            {
                "feature": col,
                "label": _label(col),
                "impact": round(float(val), 4),
                "value": round(float(row.get(col, 0)), 2),
                "direction": "raises" if val >= 0 else "lowers",
            }
            for col, val in ranked
        ]

    def _importance_fallback(self) -> dict[str, float]:
        imp = getattr(self.rm.model, "feature_importances_", None)
        if imp is None:
            return {c: 0.0 for c in self.cols}
        return dict(zip(self.cols, imp))
