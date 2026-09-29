"""Complaint DNA fingerprinting.

Encodes each complaint's modus-operandi signature (type, amount band, timing,
geography, bank) into a vector, then clusters signatures to surface organized fraud
rings that operate across different victims/locations under a common pattern.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from .data import load_all
from .features import COMPLAINT_TYPES


def compute_dna(
    n_clusters: int = 12,
    sample: int = 6000,
    state: str | None = None,
    bank: str | None = None,
) -> dict:
    """Cluster complaint signatures; return ring summaries + per-cluster stats."""
    data = load_all()
    c = data["complaints"].copy()
    if state:
        c = c[c["state"] == state]
    if bank:
        c = c[c["reported_bank"] == bank]
    if len(c) < 2:
        return {"n_clusters": 0, "rings": [], "organized_ring_count": 0}
    if len(c) > sample:
        c = c.sample(sample, random_state=42)
    n_clusters = min(n_clusters, len(c))

    c["hour"] = c["timestamp"].dt.hour
    c["dow"] = c["timestamp"].dt.dayofweek
    c["log_amount"] = np.log1p(c["fraud_amount"])
    type_oh = pd.get_dummies(c["complaint_type"]).reindex(columns=COMPLAINT_TYPES, fill_value=0)

    feats = pd.concat(
        [c[["log_amount", "hour", "dow", "lat", "lon"]].reset_index(drop=True),
         type_oh.reset_index(drop=True)], axis=1,
    )
    X = StandardScaler().fit_transform(feats)
    km = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
    c["dna_cluster"] = km.fit_predict(X)

    rings = []
    for cid, grp in c.groupby("dna_cluster"):
        districts = grp["district"].nunique()
        rings.append({
            "dna_id": int(cid),
            "size": int(len(grp)),
            "dominant_type": grp["complaint_type"].mode().iat[0],
            "districts_spanned": int(districts),
            "avg_fraud_amount": round(float(grp["fraud_amount"].mean()), 2),
            "peak_hour": int(grp["hour"].mode().iat[0]),
            # a ring is "organized" if one MO spans many districts
            "organized_ring": bool(districts >= 5 and len(grp) >= 50),
            "sample_complaint_ids": grp["complaint_id"].head(5).tolist(),
        })
    rings.sort(key=lambda r: (r["organized_ring"], r["size"]), reverse=True)
    return {
        "n_clusters": n_clusters,
        "rings": rings,
        "organized_ring_count": sum(1 for r in rings if r["organized_ring"]),
    }
