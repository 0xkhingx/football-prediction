"""API contract tests."""
from fastapi.testclient import TestClient

from api import app

client = TestClient(app)


def test_health_serves_registry_pin():
    import json

    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    reg = json.load(open("models/model_registry.json"))
    assert body["model"] == reg["model_file"]
    assert body["fair_play"] is True
    assert body["features"] == reg["n_features"]


def test_predict_roundtrip():
    r = client.post("/predict", json={"home": "Arsenal", "away": "Chelsea", "date": "2025-08-15"})
    assert r.status_code == 200
    body = r.json()
    assert body["prediction"] in ("H", "D", "A")
    assert abs(body["pH"] + body["pD"] + body["pA"] - 1.0) < 1e-6


def test_predict_rejects_same_team():
    r = client.post("/predict", json={"home": "Arsenal", "away": "Arsenal"})
    assert r.status_code == 422


def test_predict_rejects_unknown_team():
    r = client.post("/predict", json={"home": "Nope FC", "away": "Chelsea"})
    assert r.status_code == 404


def test_evaluate_disclaimer():
    body = client.get("/evaluate").json()
    assert "not betting advice" in body["disclaimer"]


def test_reload_clears_state():
    r = client.post("/reload")
    assert r.status_code == 200
    assert r.json() == {"status": "reloaded"}
    # Serving still works after reload (state rebuilds lazily).
    assert client.get("/health").status_code == 200


def test_fixtures_contract():
    r = client.get("/fixtures")
    # 200 with fixtures, or 502 when upstream is down AND no local cache.
    assert r.status_code in (200, 502)
    if r.status_code == 200:
        body = r.json()
        assert isinstance(body["fixtures"], list)
        assert body.get("source") in ("live", "local", "none")


def test_simulation_bad_league():
    assert client.get("/simulation", params={"league": "XX"}).status_code == 422
