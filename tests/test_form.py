"""Form badges + H2H from replayed history."""
from src.inference import (
    build_state_from_historical,
    form_badges,
    last_meeting,
    load_artifacts,
    predict_one,
)


def test_badges_shape_and_values():
    _, _, hist = build_state_from_historical()
    badges = form_badges(hist, "Arsenal")
    assert 0 < len(badges) <= 5
    assert set(badges) <= {"W", "D", "L"}


def test_badges_unknown_team_empty():
    _, _, hist = build_state_from_historical()
    assert form_badges(hist, "Nope FC") == []


def test_last_meeting_known_pairing():
    import pandas as pd

    _, _, hist = build_state_from_historical()
    m = last_meeting(hist, "Arsenal", "Chelsea")
    assert m is not None
    # Cross-check against source data: latest Arsenal-home or Chelsea-home meeting.
    clean = pd.read_csv("data/processed/matches_clean.csv", low_memory=False)
    pair = clean[((clean.HomeTeam == "Arsenal") & (clean.AwayTeam == "Chelsea")) |
                 ((clean.HomeTeam == "Chelsea") & (clean.AwayTeam == "Arsenal"))]
    last = pair.sort_values("Date").iloc[-1]
    assert m["date"] == str(pd.to_datetime(last["Date"]).date())
    if last["HomeTeam"] == "Arsenal":
        assert (m["home_goals"], m["away_goals"]) == (int(last["FTHG"]), int(last["FTAG"]))
    else:
        assert (m["home_goals"], m["away_goals"]) == (int(last["FTAG"]), int(last["FTHG"]))


def test_last_meeting_none_without_history():
    _, _, hist = build_state_from_historical()
    assert last_meeting(hist, "Arsenal", "Nope FC") is None


def test_predict_one_carries_form_and_h2h():
    imp, model, _ = load_artifacts()
    elo, melo, hist = build_state_from_historical()
    r = predict_one("Arsenal", "Chelsea", "2025-08-15", elo, melo, hist, imp, model)
    assert 0 < len(r["form"]["Arsenal"]) <= 5
    assert set(r["form"]["Arsenal"]) <= {"W", "D", "L"}
    assert r["h2h"] is None or set(r["h2h"]) == {"date", "home_goals", "away_goals"}
