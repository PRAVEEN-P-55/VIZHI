"""Complaint-district -> withdrawal-district transition model.

Learns, from historical complaint->withdrawal pairs, the probability that a
complaint filed in district X results in a cash-out in district Y, plus the typical
time lag. This is the core "where will the money be withdrawn" signal.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .data import load_all


def build_transition() -> dict:
    """Return transition probabilities and lag stats keyed by origin district."""
    data = load_all()
    c = data["complaints"][["complaint_id", "district"]].rename(
        columns={"district": "origin_district"}
    )
    w = data["withdrawals"].merge(
        c, left_on="linked_complaint_id", right_on="complaint_id", how="inner"
    )
    if w.empty:
        return {"origins": {}, "global_lag_hrs": 0.0}

    result: dict[str, list[dict]] = {}
    for origin, grp in w.groupby("origin_district"):
        counts = grp.groupby("withdrawal_district").agg(
            n=("withdrawal_id", "count"),
            lag=("time_since_complaint_hrs", "median"),
            amount=("amount_withdrawn", "sum"),
        )
        total = counts["n"].sum()
        rows = [
            {
                "withdrawal_district": dist,
                "probability": round(float(r["n"] / total), 4),
                "median_lag_hrs": round(float(r["lag"]), 1),
                "count": int(r["n"]),
                "total_amount": round(float(r["amount"]), 2),
                "different_district": dist != origin,
            }
            for dist, r in counts.iterrows()
        ]
        rows.sort(key=lambda x: x["probability"], reverse=True)
        result[origin] = rows

    return {
        "origins": result,
        "global_lag_hrs": round(float(w["time_since_complaint_hrs"].median()), 1),
    }


def predict_cashout(
    transition: dict,
    origin_district: str,
    top: int = 5,
    max_lag_hrs: int | None = None,
) -> list[dict]:
    """Rank likely destinations and make the requested time horizon meaningful."""
    rows = list(transition.get("origins", {}).get(origin_district, []))
    if max_lag_hrs is not None:
        rows = [r for r in rows if float(r.get("median_lag_hrs", 0)) <= max_lag_hrs]
    total = sum(float(r.get("probability", 0)) for r in rows)
    result = []
    for row in rows[:top]:
        item = dict(row)
        item["probability"] = round(float(row["probability"]) / total, 4) if total else 0.0
        item["time_bucket"] = time_bucket(float(row.get("median_lag_hrs", 0)))
        result.append(item)
    return result


def time_bucket(hours: float) -> str:
    if hours <= 6:
        return "0-6h"
    if hours <= 12:
        return "6-12h"
    if hours <= 24:
        return "12-24h"
    if hours <= 48:
        return "24-48h"
    return "48h+"


def evaluate_transition(top_values: tuple[int, ...] = (1, 3, 5)) -> dict:
    """Temporal holdout metrics for the actual withdrawal-destination task."""
    data = load_all()
    complaints = data["complaints"][["complaint_id", "district", "timestamp"]].rename(
        columns={"district": "origin_district"}
    )
    pairs = data["withdrawals"].merge(
        complaints, left_on="linked_complaint_id", right_on="complaint_id", how="inner"
    ).sort_values("timestamp")
    if pairs.empty:
        return {f"cashout_top_{k}_accuracy": 0.0 for k in top_values}

    split_at = pairs["timestamp"].quantile(0.8)
    train = pairs[pairs["timestamp"] < split_at]
    test = pairs[pairs["timestamp"] >= split_at]
    rankings = {}
    for origin, group in train.groupby("origin_district"):
        rankings[origin] = group["withdrawal_district"].value_counts().index.tolist()
    global_rank = train["withdrawal_district"].value_counts().index.tolist()

    scores = {}
    for k in top_values:
        hits = 0
        for row in test.itertuples():
            predicted = rankings.get(row.origin_district, global_rank)[:k]
            hits += int(row.withdrawal_district in predicted)
        scores[f"cashout_top_{k}_accuracy"] = round(hits / len(test), 3)
    scores["cashout_eval_pairs"] = int(len(test))
    return scores
