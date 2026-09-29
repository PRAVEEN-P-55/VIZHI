"""District risk-level classifier + Precision@K evaluation.

Trains a gradient-boosted classifier on the district-week feature table to predict
`risk_level` (LOW/MEDIUM/HIGH). Uses XGBoost when available, otherwise falls back
to scikit-learn's GradientBoostingClassifier so the pipeline is resilient.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, f1_score

from .features import RISK_ORDER, build_feature_table, feature_columns

RISK_INV = {v: k for k, v in RISK_ORDER.items()}

try:  # prefer XGBoost
    from xgboost import XGBClassifier

    _HAS_XGB = True
except Exception:  # pragma: no cover - fallback path
    from sklearn.ensemble import GradientBoostingClassifier

    _HAS_XGB = False


@dataclass
class RiskModel:
    model: object
    columns: list[str]
    metrics: dict = field(default_factory=dict)
    backend: str = "xgboost"

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        return self.model.predict_proba(X[self.columns])

    def predict_label(self, X: pd.DataFrame) -> list[str]:
        idx = self.model.predict(X[self.columns])
        return [RISK_INV[int(i)] for i in idx]


def _new_model():
    if _HAS_XGB:
        return XGBClassifier(
            n_estimators=300,
            max_depth=4,
            learning_rate=0.08,
            subsample=0.9,
            colsample_bytree=0.9,
            objective="multi:softprob",
            num_class=3,
            eval_metric="mlogloss",
            n_jobs=0,
            random_state=42,
        )
    return GradientBoostingClassifier(random_state=42)


def precision_at_k(df_test: pd.DataFrame, proba: np.ndarray, k: int = 5) -> float:
    """Mean Precision@K across test weeks.

    For each week, rank districts by predicted P(HIGH); of the top-K, what fraction
    were actually HIGH risk. This mirrors the operational question: "did the real
    high-risk withdrawal zones fall inside our top-K predicted zones?"
    """
    high_idx = RISK_ORDER["HIGH"]
    tmp = df_test.copy()
    tmp["p_high"] = proba[:, high_idx]
    scores = []
    for _, wk in tmp.groupby("week_start"):
        top = wk.sort_values("p_high", ascending=False).head(k)
        if len(top) == 0:
            continue
        hits = (top["y"] == high_idx).sum()
        scores.append(hits / min(k, len(top)))
    return float(np.mean(scores)) if scores else 0.0


def train_risk_model(k: int = 5) -> RiskModel:
    df = build_feature_table()
    df = df.dropna(subset=["y"]).copy()
    df["y"] = df["y"].astype(int)
    cols = feature_columns()

    # time-based split: last ~20% of weeks held out
    weeks = np.sort(df["week_start"].unique())
    split = weeks[int(len(weeks) * 0.8)]
    train = df[df["week_start"] < split]
    test = df[df["week_start"] >= split]

    model = _new_model()
    model.fit(train[cols], train["y"])

    proba = model.predict_proba(test[cols])
    preds = model.predict(test[cols])
    macro_f1 = float(f1_score(test["y"], preds, average="macro"))
    p_at_k = precision_at_k(test, proba, k=k)
    report = classification_report(
        test["y"], preds, target_names=["LOW", "MEDIUM", "HIGH"],
        output_dict=True, zero_division=0,
    )

    metrics = {
        "macro_f1": round(macro_f1, 3),
        f"precision_at_{k}": round(p_at_k, 3),
        "n_train": int(len(train)),
        "n_test": int(len(test)),
        "backend": "xgboost" if _HAS_XGB else "sklearn-gbc",
        "per_class": {c: round(report[c]["f1-score"], 3) for c in ["LOW", "MEDIUM", "HIGH"]},
    }
    return RiskModel(model=model, columns=cols, metrics=metrics,
                     backend="xgboost" if _HAS_XGB else "sklearn-gbc")
