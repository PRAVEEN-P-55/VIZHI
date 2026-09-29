"""Complaint-volume time-series forecast.

Forecasts daily complaint volume to anticipate spikes (which precede withdrawal
waves). Uses statsmodels Holt-Winters; Prophet is used automatically if installed.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .data import load_all


def _forecast_holt_winters(series: pd.Series, horizon: int) -> np.ndarray:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    model = ExponentialSmoothing(
        series, trend="add", seasonal="add", seasonal_periods=7,
        initialization_method="estimated",
    ).fit()
    return np.asarray(model.forecast(horizon))


def _forecast_prophet(daily: pd.DataFrame, horizon: int):  # pragma: no cover
    from prophet import Prophet

    m = Prophet(daily_seasonality=False, weekly_seasonality=True, yearly_seasonality=False)
    m.fit(daily.rename(columns={"date": "ds", "count": "y"}))
    future = m.make_future_dataframe(periods=horizon)
    fc = m.predict(future).tail(horizon)
    return fc["yhat"].to_numpy()


def forecast_complaints(
    horizon: int = 14,
    state: str | None = None,
    bank: str | None = None,
) -> dict:
    """Return recent history + forecast + spike flags."""
    data = load_all()
    c = data["complaints"].copy()
    if state:
        c = c[c["state"] == state]
    if bank:
        c = c[c["reported_bank"] == bank]
    if c.empty:
        return {"backend": "none", "baseline": 0, "spike_threshold": 0,
                "history": [], "forecast": []}
    c["date"] = c["timestamp"].dt.floor("D")
    daily = c.groupby("date").size().reset_index(name="count").sort_values("date")
    series = daily.set_index("date")["count"].asfreq("D").fillna(0)

    backend = "holt-winters"
    try:
        yhat = _forecast_prophet(daily, horizon)
        backend = "prophet"
    except Exception:
        try:
            yhat = _forecast_holt_winters(series, horizon)
        except Exception:
            # last-resort: weekday-seasonal moving average
            yhat = np.full(horizon, series.tail(28).mean())

    yhat = np.clip(yhat, 0, None)
    last_date = series.index.max()
    future_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=horizon)

    baseline = float(series.tail(28).mean())
    threshold = baseline * 1.25
    forecast = [
        {
            "date": d.strftime("%Y-%m-%d"),
            "predicted": round(float(v), 1),
            "spike": bool(v > threshold),
        }
        for d, v in zip(future_dates, yhat)
    ]
    history = [
        {"date": d.strftime("%Y-%m-%d"), "count": int(v)}
        for d, v in series.tail(90).items()
    ]
    return {
        "backend": backend,
        "baseline": round(baseline, 1),
        "spike_threshold": round(threshold, 1),
        "history": history,
        "forecast": forecast,
    }
