from pydantic import ValidationError

from app.ml.transition import time_bucket
from app.schemas import CasePredictRequest, DispatchRequest, PredictRequest


def test_time_buckets_cover_operational_horizon():
    assert time_bucket(4) == "0-6h"
    assert time_bucket(10) == "6-12h"
    assert time_bucket(18) == "12-24h"
    assert time_bucket(36) == "24-48h"
    assert time_bucket(60) == "48h+"


def test_prediction_window_validation():
    assert PredictRequest(window_hrs=24).window_hrs == 24
    try:
        PredictRequest(window_hrs=2)
    except ValidationError:
        pass
    else:
        raise AssertionError("window below six hours must be rejected")


def test_case_request_accepts_complaint_lookup():
    request = CasePredictRequest(complaint_id="CMP-1", top_k=3)
    assert request.complaint_id == "CMP-1"
    assert request.window_hrs == 48


def test_dispatch_channels_are_normalized_and_independent():
    first = DispatchRequest(channels=["dashboard", "email"])
    second = DispatchRequest()
    assert first.channels == ["in_app", "email"]
    assert second.channels == ["in_app", "sms", "email"]
