"""Fixtures + scoreline edge paths (previously untested)."""
from src.goals import select_scoreline
from src.inference import score_for_fixture
from src.predict_live import current_season_code, fetch_local_fixtures


def test_current_season_code():
    assert current_season_code("2026-09-08") == "2627"
    assert current_season_code("2026-01-15") == "2526"
    assert current_season_code("2026-07-01") == "2627"


def test_local_fixtures_schema():
    fx = fetch_local_fixtures()
    assert set(("Div", "HomeTeam", "AwayTeam", "Date")) <= set(fx.columns)
    assert (fx["Div"].isin(["E0", "SP1", "I1", "D1", "F1"]).all() if len(fx) else True)


def test_local_fixtures_carry_round():
    import pandas as pd

    raw = pd.read_csv("data/fixtures_2627.csv")
    assert "Round" in raw.columns
    fx = fetch_local_fixtures()
    if len(fx):
        assert "Round" in fx.columns
        assert fx["Round"].str.contains("Matchday").any()


def test_score_for_fixture_unknown_teams_is_none():
    assert score_for_fixture("Nope FC", "Also Nope", "2026-09-08", None, "H", True) is None


def test_select_scoreline_no_call_hidden():
    sel = select_scoreline({"conditional": {"H": [{"h": 1, "a": 0, "p": 0.1}]}},
                           "H", False)
    assert sel == {"shown": False, "reason": "XGB too close to call — no scoreline stamped"}


def test_select_scoreline_picks_conditional():
    sel = select_scoreline({"conditional": {"A": [{"h": 0, "a": 1, "p": 0.09}]}},
                           "A", True)
    assert sel["shown"] is True and (sel["h"], sel["a"]) == (0, 1)
