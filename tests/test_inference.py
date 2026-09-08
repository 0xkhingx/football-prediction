"""Inference: fair-play guard, shapes, determinism, serving model."""
import numpy as np
import pytest

from src.config import FEATURE_COLS_NO_ODDS
from src.inference import (
    build_state_from_historical,
    featurize_fixture,
    guard_no_odds,
    load_artifacts,
    predict_one,
    vectorize,
)


def test_guard_rejects_odds():
    with pytest.raises(ValueError):
        guard_no_odds({"ProbB365H": 0.5})


def test_featurize_order_and_shape():
    elo, melo, hist = build_state_from_historical()
    assert len(hist) > 100  # history replayed, not empty
    f = featurize_fixture("Arsenal", "Chelsea", "2025-08-15", elo, melo, hist)
    assert list(f.keys()) == FEATURE_COLS_NO_ODDS
    x = vectorize(f)
    assert x.shape == (1, len(FEATURE_COLS_NO_ODDS))


def test_predict_proba_sums_to_one():
    import json

    imp, model, name = load_artifacts()
    reg = json.load(open("models/model_registry.json"))
    assert name == reg["model_file"], "serving file must match registry pin"
    assert name.endswith(".joblib")
    elo, melo, hist = build_state_from_historical()
    r = predict_one("Arsenal", "Chelsea", "2025-08-15", elo, melo, hist, imp, model)
    p = r["probabilities"]
    assert r["prediction"] in ("H", "D", "A")
    assert abs(p["H"] + p["D"] + p["A"] - 1.0) < 1e-6
    assert 0 <= r["confidence"] <= 1


def test_determinism():
    imp, model, _ = load_artifacts()
    elo, melo, hist = build_state_from_historical()
    a = predict_one("Real Madrid", "Barcelona", "2025-08-15", elo, melo, hist, imp, model)
    b = predict_one("Real Madrid", "Barcelona", "2025-08-15", elo, melo, hist, imp, model)
    assert a["probabilities"] == b["probabilities"]
