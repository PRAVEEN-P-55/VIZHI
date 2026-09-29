"""Feature engineering for the district-week risk classifier.

Builds one feature row per (district, week_start), aligned to the weekly grain of
`district_risk_labels`, enriching the supplied counts with engineered signals from
complaints, withdrawals, and mule linkages, plus prior-week lag features.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .data import load_all

COMPLAINT_TYPES = ["UPI Fraud", "OTP Scam", "KYC Fraud", "Job Fraud", "Loan App Fraud"]
RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
WEEK_RULE = "W-SAT"  # weeks start Sunday (dataset weeks begin 2024-09-01, a Sunday)


def _week_start(ts: pd.Series) -> pd.Series:
    return ts.dt.to_period(WEEK_RULE).dt.start_time


def build_feature_table() -> pd.DataFrame:
    """Return a feature matrix merged with the `risk_level` target."""
    data = load_all()
    complaints = data["complaints"].copy()
    withdrawals = data["withdrawals"].copy()
    mules = data["mules"].copy()
    labels = data["labels"].copy()

    complaints["week_start"] = _week_start(complaints["timestamp"])
    complaints["dow"] = complaints["timestamp"].dt.dayofweek  # 0=Mon..6=Sun
    complaints["is_weekend"] = complaints["dow"].isin([4, 5, 6]).astype(int)  # Fri-Sun

    # ---- complaint-derived aggregates per district-week ----
    grp = complaints.groupby(["district", "week_start"])
    feats = grp.agg(
        c_mean_fraud=("fraud_amount", "mean"),
        c_max_fraud=("fraud_amount", "max"),
        c_unique_pins=("pin_code", "nunique"),
        c_unique_banks=("reported_bank", "nunique"),
        c_weekend_ratio=("is_weekend", "mean"),
    ).reset_index()

    # complaint-type mix (proportions)
    type_counts = (
        complaints.pivot_table(
            index=["district", "week_start"],
            columns="complaint_type",
            values="complaint_id",
            aggfunc="count",
            fill_value=0,
        )
        .reset_index()
    )
    for t in COMPLAINT_TYPES:
        if t not in type_counts.columns:
            type_counts[t] = 0
    tot = type_counts[COMPLAINT_TYPES].sum(axis=1).replace(0, 1)
    for t in COMPLAINT_TYPES:
        type_counts[f"prop_{t.replace(' ', '_')}"] = type_counts[t] / tot
    prop_cols = [f"prop_{t.replace(' ', '_')}" for t in COMPLAINT_TYPES]
    type_counts = type_counts[["district", "week_start", *prop_cols]]

    # ---- withdrawal-derived aggregates per landing district-week ----
    withdrawals["week_start"] = _week_start(withdrawals["withdrawal_timestamp"])
    wgrp = withdrawals.groupby(["withdrawal_district", "week_start"]).agg(
        w_sum_amount=("amount_withdrawn", "sum"),
        w_mean_lag_hrs=("time_since_complaint_hrs", "mean"),
    ).reset_index().rename(columns={"withdrawal_district": "district"})

    # ---- mule linkage counts per district-week (via linked complaints) ----
    link_rows: list[tuple[str, object]] = []
    cmap = complaints.set_index("complaint_id")[["district", "week_start"]]
    for ids in mules["linked_complaint_ids"]:
        try:
            for cid in json.loads(ids):
                if cid in cmap.index:
                    r = cmap.loc[cid]
                    link_rows.append((r["district"], r["week_start"]))
        except Exception:
            continue
    if link_rows:
        mule_df = pd.DataFrame(link_rows, columns=["district", "week_start"])
        mule_feat = (
            mule_df.groupby(["district", "week_start"]).size().reset_index(name="mule_links")
        )
    else:
        mule_feat = pd.DataFrame(columns=["district", "week_start", "mule_links"])

    # ---- merge everything onto the label grid ----
    df = labels.copy()
    df = df.merge(feats, on=["district", "week_start"], how="left")
    df = df.merge(type_counts, on=["district", "week_start"], how="left")
    df = df.merge(wgrp, on=["district", "week_start"], how="left")
    df = df.merge(mule_feat, on=["district", "week_start"], how="left")

    # ---- lag features (previous week per district) ----
    df = df.sort_values(["district", "week_start"])
    for col in ["complaint_count", "withdrawal_count", "total_fraud_amount"]:
        df[f"{col}_lag1"] = df.groupby("district")[col].shift(1)
    df["risk_lag1"] = (
        df.groupby("district")["risk_level"].shift(1).map(RISK_ORDER)
    )

    df = df.fillna(0.0)
    # Predictive target: NEXT week's risk for the district (true forecasting).
    # Same-week counts define the label, so predicting the same week leaks the
    # answer; shifting the target one week ahead makes this genuinely predictive
    # and yields honest metrics. The final week per district has no next-week
    # label (y is NaN) but is kept for inference — training drops those rows.
    df["risk_next"] = df.groupby("district")["risk_level"].shift(-1)
    df["y_current"] = df["risk_level"].map(RISK_ORDER).astype(int)
    df["y"] = df["risk_next"].map(RISK_ORDER)
    return df


def feature_columns() -> list[str]:
    base = [
        "complaint_count", "total_fraud_amount", "withdrawal_count",
        "c_mean_fraud", "c_max_fraud", "c_unique_pins", "c_unique_banks",
        "c_weekend_ratio", "w_sum_amount", "w_mean_lag_hrs", "mule_links",
        "complaint_count_lag1", "withdrawal_count_lag1", "total_fraud_amount_lag1",
        "risk_lag1",
    ]
    props = [f"prop_{t.replace(' ', '_')}" for t in COMPLAINT_TYPES]
    return base + props
