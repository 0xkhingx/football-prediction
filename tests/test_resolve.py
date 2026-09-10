"""Team resolution: exact/alias/stripped/fuzzy layers + honest refusals."""
import pytest

from src.config import AMBIGUOUS_STUBS
from src.inference import (
    build_state_from_historical,
    normalize_team,
    resolve_team,
    strip_suffix,
)


@pytest.fixture(scope="module")
def teams():
    _, _, hist = build_state_from_historical()
    return list(hist)


def test_normalize_and_strip():
    assert normalize_team("  ARSENAL  ") == "arsenal"
    assert strip_suffix("arsenal fc") == "arsenal"
    assert strip_suffix("valencia cf") == "valencia"
    assert strip_suffix("levante ud") == "levante"
    assert strip_suffix("arsenal") == "arsenal"


def test_exact_case_insensitive(teams):
    assert resolve_team("arsenal", teams)["team"] == "Arsenal"
    assert resolve_team("arsenal", teams)["method"] == "exact"


def test_aliases(teams):
    for raw, want in [("Man Utd", "Manchester United"), ("man city", "Manchester City"),
                      ("Spurs", "Tottenham Hotspur"), ("Hammers", "West Ham United"),
                      ("Toon", "Newcastle United"), ("PSG", "Paris Saint-Germain"),
                      ("Juve", "Juventus"), ("Bayern", "Bayern Munich"),
                      ("BVB", "Dortmund"), ("Atleti", "Atletico Madrid"),
                      ("Barca", "Barcelona"), ("Schalke", "Schalke 04"),
                      ("Koln", "FC Cologne"), ("St Pauli", "FC St Pauli")]:
        r = resolve_team(raw, teams)
        assert r["team"] == want, raw
        assert r["method"] == "alias", raw


def test_suffix_strip(teams):
    assert resolve_team("Arsenal FC", teams)["method"] == "stripped"
    assert resolve_team("Elche CF", teams)["team"] == "Elche"


def test_fuzzy_typos_accepted(teams):
    assert resolve_team("Arseanl", teams)["team"] == "Arsenal"
    assert resolve_team("Arseanl", teams)["method"] == "fuzzy"
    assert resolve_team("Newcastel", teams)["team"] == "Newcastle United"


def test_ambiguous_never_guessed(teams):
    for stub in list(AMBIGUOUS_STUBS) + ["paris"]:
        r = resolve_team(stub, teams)
        assert r["team"] is None, stub


def test_garbage_rejected_without_suggestion(teams):
    r = resolve_team("Xyz FC", teams)
    assert r["team"] is None
    assert r["suggestion"] is None


def test_alias_target_missing_is_ignored():
    teams = ["Arsenal", "Chelsea"]
    r = resolve_team("bvb", teams)
    assert r["team"] is None  # Dortmund not in this set: no phantom match


def test_api_resolved_field_and_suggestion():
    from fastapi.testclient import TestClient

    from api import app

    c = TestClient(app)
    body = c.post("/predict", json={"home": "arsenal", "away": "Spurs"}).json()
    assert "home" not in body["resolved"]  # exact needs no note
    assert body["resolved"]["away"] == {"from": "Spurs", "to": "Tottenham Hotspur", "via": "alias"}

    exact = c.post("/predict", json={"home": "Arsenal", "away": "Chelsea"}).json()
    assert exact["resolved"] is None

    bad = c.post("/predict", json={"home": "Xyz FC", "away": "Chelsea"})
    assert bad.status_code == 404
    assert "did you mean" not in bad.json()["detail"]  # garbage: no suggestion

    typo = c.post("/predict", json={"home": "Arseanl", "away": "Chelsea"})
    assert typo.status_code == 200
    assert typo.json()["resolved"]["home"]["via"] == "fuzzy"
