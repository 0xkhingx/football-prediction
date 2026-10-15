"""Regressions for point-in-time serving, fixture ingress and production safety."""
import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from src.inference import build_state_from_historical, featurize_fixture
from src.predict_live import normalize_fixtures


def test_history_cutoff_excludes_match_day_and_later_results(tmp_path):
    rows = pd.DataFrame([
        {"Date": date, "League": "E0", "HomeTeam": "Arsenal", "AwayTeam": "Chelsea",
         "FTHG": hg, "FTAG": ag, "FTR": result}
        for date, hg, ag, result in [
            ("2026-08-01", 1, 0, "H"), ("2026-08-08", 0, 4, "A"),
            ("2026-08-15", 0, 5, "A"),
        ]
    ])
    path = tmp_path / "matches.csv"
    rows.to_csv(path, index=False)
    state = build_state_from_historical(path, as_of="2026-08-08")
    rows.iloc[:1].to_csv(path, index=False)
    expected = build_state_from_historical(path)
    assert state[:2] == expected[:2]
    feats = featurize_fixture("Arsenal", "Chelsea", "2026-08-08", *state)
    assert feats["HomeForm5"] == 1
    assert feats["HomeRest"] == 7
    assert len(state[2]["Arsenal"]) == 1


def test_fixture_normalization_preserves_calendar_and_training_identity():
    df = normalize_fixtures(pd.DataFrame({
        "HomeTeam": ["Man City", "Man United", "Arsenal", "Chelsea"],
        "AwayTeam": ["Tottenham", "West Ham", "Chelsea", "Arsenal"],
        "Date": ["09/10/2026", "2026-11-01", "01/02/26", "invalid"],
        "Div": ["E0"] * 4,
    }))
    assert df["Date"].tolist() == ["2026-10-09", "2026-11-01", "2026-02-01"]
    assert df["HomeTeam"].tolist() == ["Manchester City", "Manchester United", "Arsenal"]
    assert df["AwayTeam"].tolist()[:2] == ["Tottenham Hotspur", "West Ham United"]


def test_rate_limit_ignores_spoofed_headers_and_expires_clients(monkeypatch):
    from fastapi import HTTPException
    from src import ratelimit

    monkeypatch.setattr(ratelimit, "_windows", {})
    monkeypatch.setattr(ratelimit, "_last_sweep", 0.0)
    monkeypatch.setattr(ratelimit.time, "monotonic", lambda: 100.0)
    for i in range(ratelimit.BURST):
        req = SimpleNamespace(client=SimpleNamespace(host="real-client"),
                              headers={"x-forwarded-for": f"spoof-{i}"})
        ratelimit.check(req, "predict")
    with pytest.raises(HTTPException) as exc:
        ratelimit.check(req, "predict")
    assert exc.value.status_code == 429
    assert len(ratelimit._windows) == 1
    monkeypatch.setattr(ratelimit.time, "monotonic", lambda: 200.0)
    req.client.host = "new-client"
    ratelimit.check(req, "predict")
    assert list(ratelimit._windows) == [("new-client", "predict")]


def test_live_feed_normalizes_before_returning_to_api_and_cli(monkeypatch):
    from src import predict_live

    response = SimpleNamespace(status_code=200, text=(
        "Div,Date,HomeTeam,AwayTeam\n"
        "E0,09/10/2099,Man City,Tottenham\n"
        "E0,01/01/2000,Arsenal,Chelsea\n"
    ))
    monkeypatch.setattr(predict_live.requests, "get", lambda *a, **k: response)
    fx = predict_live.fetch_fixtures()
    assert len(fx) == 1
    assert fx.iloc[0]["HomeTeam"] == "Manchester City"
    assert fx.iloc[0]["AwayTeam"] == "Tottenham Hotspur"
    assert fx.iloc[0]["Date"] == "2099-10-09"
    assert fx.attrs["source"] == "live"


def test_empty_fixture_feed_is_normalized():
    df = pd.DataFrame(columns=["HomeTeam", "AwayTeam", "Date", "Div"])
    assert normalize_fixtures(df).empty


def test_santander_uses_same_identity_as_openfootball():
    df = pd.DataFrame([{"HomeTeam": "Santander", "AwayTeam": "Villarreal", "Date": "16/08/2026"}])
    assert normalize_fixtures(df).iloc[0]["HomeTeam"] == "Racing"


def test_rate_limit_bounds_active_clients(monkeypatch):
    from fastapi import HTTPException
    from src import ratelimit

    monkeypatch.setattr(ratelimit, "_windows", {})
    monkeypatch.setattr(ratelimit, "MAX_CLIENTS", 1)
    for host in ["first", "second"]:
        req = SimpleNamespace(client=SimpleNamespace(host=host), headers={})
        if host == "first":
            ratelimit.check(req, "predict")
        else:
            with pytest.raises(HTTPException):
                ratelimit.check(req, "predict")
    assert len(ratelimit._windows) == 1


def test_completed_season_still_has_champion_and_top_four(monkeypatch):
    from src import simulate

    monkeypatch.setattr(simulate.pd, "read_csv", lambda *a, **k: pd.DataFrame())
    monkeypatch.setattr(simulate, "current_table", lambda *a: dict(A=90, B=80, C=70, D=60, E=50))
    monkeypatch.setattr(simulate, "remaining_fixtures",
                        lambda *a: pd.DataFrame(columns=["Home", "Away", "Date"]))
    monkeypatch.setattr(simulate, "build_state_from_historical", lambda: ({}, {}, {}))
    monkeypatch.setattr(simulate, "load_artifacts", lambda: (None, None, "unused"))
    result = simulate.simulate_league("E0", n_sims=10)
    assert sum(r["title_raw"] for r in result["table"]) == 1
    assert sum(r["top4_raw"] for r in result["table"]) == 4
    assert result["table"][0]["team"] == "A"
    assert result["table"][0]["title_raw"] == 1
    assert result["table"][-1]["top4_raw"] == 0


def test_retraining_does_not_promote_ensemble(tmp_path, monkeypatch):
    from src import train_tuned_prod as train

    class FakeXGB:
        best_iteration = 0

        def fit(self, *args, **kwargs):
            return self

        def predict_proba(self, x):
            return np.tile([0.5, 0.3, 0.2], (len(x), 1))

        def save_model(self, path):
            pass

    rng = np.random.default_rng(42)
    split = tmp_path / "splits.npz"
    np.savez(split, **{f"{prefix}_{part}": value
                      for part, n in [("train", 30), ("val", 12), ("test", 12)]
                      for prefix, value in [("X", rng.normal(size=(n, 23))),
                                            ("y", np.arange(n) % 3)]})
    params = tmp_path / "params.json"
    params.write_text("{}")
    meta = tmp_path / "meta.json"
    meta.write_text(json.dumps(dict(train_seasons=[2425], val_season=2526, test_season=2627)))
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({"ensemble": {"xgb_weight": 1.0, "calibrators": ""}}))
    for name, path in [("SPLITS_FILE", split), ("TUNED_PARAMS_FILE", params),
                       ("META_FILE", meta), ("MODEL_DIR", tmp_path), ("REGISTRY_FILE", registry)]:
        monkeypatch.setattr(train, name, path)
    monkeypatch.setattr(train.xgb, "XGBClassifier", lambda **k: FakeXGB())
    monkeypatch.setattr(train.joblib, "dump", lambda *a: None)
    train.main()
    result = json.loads(registry.read_text())
    assert result["ensemble"]["xgb_weight"] == 1.0
    assert result["ensemble"]["calibrators"] == ""
    assert result["candidate_ensemble"]["calibrators"]
    assert result["metrics"]["test_log_loss"] == result["components"]["xgb"]["test_log_loss"]
