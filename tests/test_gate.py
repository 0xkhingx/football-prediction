"""Honesty gate: boundary behavior + API contract."""
import numpy as np

from src.config import MIN_CONFIDENCE
from src.inference import apply_honesty_gate


def test_threshold_in_sane_range():
    assert 0.3 < MIN_CONFIDENCE < 0.6


def test_below_threshold_is_no_call():
    g = apply_honesty_gate(np.array([0.44, 0.33, 0.23]))
    assert g["call"] is False
    assert g["label"] == "TOO CLOSE TO CALL"


def test_at_threshold_is_call():
    g = apply_honesty_gate(np.array([0.45, 0.30, 0.25]))
    assert g["call"] is True
    assert g["label"] == "MODEL CALLS H"


def test_call_labels_winner():
    g = apply_honesty_gate(np.array([0.2, 0.25, 0.55]))
    assert g["call"] is True and g["label"] == "MODEL CALLS A"
    assert g["threshold"] == MIN_CONFIDENCE


def test_api_response_carries_gate():
    from fastapi.testclient import TestClient

    from api import app

    body = TestClient(app).post(
        "/predict", json={"home": "Arsenal", "away": "Chelsea", "date": "2025-08-15"}
    ).json()
    assert set(("call", "call_label")) <= set(body)
    assert body["call"] == (body["confidence"] >= MIN_CONFIDENCE)
