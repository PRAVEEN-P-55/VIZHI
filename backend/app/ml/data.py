"""Dataframe loaders for the ML layer.

Reads directly from the database with pandas — simpler and faster for vectorized
feature engineering than going row-by-row through the ORM.
"""
from __future__ import annotations

import functools

import pandas as pd

from ..db import engine


def _read(table: str, parse_dates: list[str] | None = None) -> pd.DataFrame:
    df = pd.read_sql_table(table, engine, parse_dates=parse_dates)
    # SQLAlchemy may return `quoted_name` column labels; force plain str so
    # downstream sklearn/SHAP feature-name validation is happy.
    df.columns = [str(c) for c in df.columns]
    return df


@functools.lru_cache(maxsize=1)
def load_all() -> dict[str, pd.DataFrame]:
    """Load every table once and cache. Call `load_all.cache_clear()` after reingest."""
    complaints = _read("complaints", parse_dates=["timestamp"])
    withdrawals = _read("withdrawals", parse_dates=["withdrawal_timestamp"])
    atms = _read("atm_locations")
    mules = _read("mule_accounts")
    labels = _read("district_risk_labels", parse_dates=["week_start"])
    return {
        "complaints": complaints,
        "withdrawals": withdrawals,
        "atms": atms,
        "mules": mules,
        "labels": labels,
    }


def clear_cache() -> None:
    load_all.cache_clear()
