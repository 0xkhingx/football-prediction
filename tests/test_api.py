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


def test_reload_clears_state(monkeypatch):
    monkeypatch.setenv("RELOAD_TOKEN", "s3cret")
    r = client.post("/reload", headers={"Authorization": "Bearer s3cret"})
    assert r.status_code == 200
    assert r.json() == {"status": "reloaded"}
    # Serving still works after reload (state rebuilds lazily).
    assert client.get("/health").status_code == 200


def test_reload_requires_token(monkeypatch):
    import api as api_module

    monkeypatch.setenv("RELOAD_TOKEN", "s3cret")
    assert client.post("/reload").status_code == 403  # no token presented
    assert client.post("/reload", headers={"Authorization": "Bearer wrong"}).status_code == 403
    ok = client.post("/reload", headers={"Authorization": "Bearer s3cret"})
    assert ok.status_code == 200
    assert api_module._state.cache_info().currsize == 0  # cache actually dropped
    monkeypatch.delenv("RELOAD_TOKEN", raising=False)


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


def test_rate_limit_kicks_in():
    from fastapi import HTTPException

    from src import ratelimit
    from src.ratelimit import BURST, check

    class FakeClient:
        host = "rate-test-client"

    class FakeRequest:
        headers = {}
        client = FakeClient()

    ratelimit._windows.clear()
    for _ in range(BURST):
        check(FakeRequest(), "test-route")
    try:
        check(FakeRequest(), "test-route")
        raise AssertionError("expected 429")
    except HTTPException as e:
        assert e.status_code == 429
        assert "Retry-After" in (e.headers or {})
    finally:
        ratelimit._windows.clear()
