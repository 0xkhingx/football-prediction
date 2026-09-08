"""Dixon-Coles scorelines: sanity, consistency selection, league inference."""
from src.goals import (
    cached_matches,
    predict_scorelines,
    select_scoreline,
    team_league_map,
)


def test_top_scoreline_shape():
    df = cached_matches()
    sc = predict_scorelines("Arsenal", "Chelsea", "E0", "2025-08-15", df)
    assert abs((sc["pH"] + sc["pD"] + sc["pA"]) - 1.0) < 1e-6
    assert len(sc["top"]) == 3
    assert sc["top"][0]["p"] >= sc["top"][1]["p"] >= sc["top"][2]["p"]


def test_strong_favorite_has_high_lambda():
    df = cached_matches()
    sc = predict_scorelines("Paris Saint-Germain", "Angers", "F1", "2025-08-15", df)
    assert sc["lambda_home"] > sc["lambda_away"]
    assert sc["outcome"] == "H"


def test_conditional_pick_agrees_with_xgb_by_construction():
    df = cached_matches()
    sc = predict_scorelines("Arsenal", "Chelsea", "E0", "2025-08-15", df)
    sel = select_scoreline(sc, "H", True)
    assert sel["shown"] is True
    assert sel["h"] > sel["a"]  # conditional on H must imply H


def test_no_call_hides_scoreline():
    df = cached_matches()
    sc = predict_scorelines("Arsenal", "Chelsea", "E0", "2025-08-15", df)
    sel = select_scoreline(sc, "H", False)
    assert sel["shown"] is False


def test_league_inference():
    assert team_league_map()["Arsenal"] == "E0"
    assert team_league_map()["Real Madrid"] == "SP1"
    assert "Nope FC" not in team_league_map()
