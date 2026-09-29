"""Geospatial hotspot clustering via DBSCAN (haversine).

Clusters historical withdrawal points into hotspot zones for the risk heatmap.
Each zone carries a centroid, radius, count, dominant bank, and nearest landmark.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN

from .data import load_all

EARTH_KM = 6371.0088


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    d = (
        np.sin((lat2 - lat1) / 2) ** 2
        + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    )
    return float(2 * EARTH_KM * np.arcsin(np.sqrt(d)))


def compute_hotspots(eps_km: float = 3.0, min_samples: int = 8) -> list[dict]:
    """Return withdrawal hotspot zones, most active first."""
    data = load_all()
    w = data["withdrawals"].dropna(subset=["withdrawal_lat", "withdrawal_lon"]).copy()
    if w.empty:
        return []

    coords = np.radians(w[["withdrawal_lat", "withdrawal_lon"]].to_numpy())
    labels = DBSCAN(
        eps=eps_km / EARTH_KM, min_samples=min_samples, metric="haversine"
    ).fit_predict(coords)
    w["cluster"] = labels

    atms = data["atms"]
    zones: list[dict] = []
    for cid, grp in w[w["cluster"] >= 0].groupby("cluster"):
        clat = float(grp["withdrawal_lat"].mean())
        clon = float(grp["withdrawal_lon"].mean())
        radius = max(
            _haversine_km(clat, clon, r.withdrawal_lat, r.withdrawal_lon)
            for r in grp.itertuples()
        )
        # nearest ATM landmark
        landmark = None
        if not atms.empty:
            d = atms.apply(
                lambda a: _haversine_km(clat, clon, a["lat"], a["lon"]), axis=1
            )
            landmark = atms.loc[d.idxmin(), "near_landmark"]
        zones.append({
            "cluster_id": int(cid),
            "lat": round(clat, 5),
            "lon": round(clon, 5),
            "radius_km": round(radius, 2),
            "withdrawal_count": int(len(grp)),
            "total_amount": round(float(grp["amount_withdrawn"].sum()), 2),
            "dominant_bank": grp["bank_name"].mode().iat[0] if not grp["bank_name"].mode().empty else None,
            "dominant_district": grp["withdrawal_district"].mode().iat[0],
            "near_landmark": landmark,
        })
    zones.sort(key=lambda z: z["withdrawal_count"], reverse=True)
    return zones
