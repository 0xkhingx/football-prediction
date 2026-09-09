"""Log immutability: re-runs must never rewrite logged calls."""
import pandas as pd

import src.predict_live as pl


def test_append_never_overwrites(tmp_path, monkeypatch):
    log = tmp_path / "predictions_log.csv"
    monkeypatch.setattr(pl, "PREDICTIONS_LOG", log)
    first = pd.DataFrame([{
        "Date": "2026-09-12", "League": "E0", "Home": "Arsenal", "Away": "Chelsea",
        "Prediction": "H", "Confidence": 0.6, "P(H)": 0.6, "P(D)": 0.25, "P(A)": 0.15,
        "Call": True, "CallLabel": "MODEL CALLS H",
    }])
    pl.append_predictions(first)
    # Re-run after the match with a different (recomputed) call: log must keep the original.
    second = pd.DataFrame([{
        "Date": "2026-09-12", "League": "E0", "Home": "Arsenal", "Away": "Chelsea",
        "Prediction": "A", "Confidence": 0.9, "P(H)": 0.05, "P(D)": 0.05, "P(A)": 0.9,
        "Call": True, "CallLabel": "MODEL CALLS A",
    }])
    combined = pl.append_predictions(second)
    assert len(combined) == 1
    assert combined.iloc[0]["Prediction"] == "H"
    assert combined.iloc[0]["Confidence"] == 0.6
    assert pd.read_csv(log).iloc[0]["Prediction"] == "H"


def test_append_adds_new_fixtures(tmp_path, monkeypatch):
    log = tmp_path / "predictions_log.csv"
    monkeypatch.setattr(pl, "PREDICTIONS_LOG", log)
    pl.append_predictions(pd.DataFrame([{
        "Date": "2026-09-12", "League": "E0", "Home": "Arsenal", "Away": "Chelsea",
        "Prediction": "H", "Confidence": 0.6, "P(H)": 0.6, "P(D)": 0.25, "P(A)": 0.15,
        "Call": True, "CallLabel": "MODEL CALLS H",
    }]))
    combined = pl.append_predictions(pd.DataFrame([{
        "Date": "2026-09-13", "League": "E0", "Home": "Liverpool", "Away": "Everton",
        "Prediction": "H", "Confidence": 0.7, "P(H)": 0.7, "P(D)": 0.2, "P(A)": 0.1,
        "Call": True, "CallLabel": "MODEL CALLS H",
    }]))
    assert len(combined) == 2
