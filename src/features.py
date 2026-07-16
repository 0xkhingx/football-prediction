import pandas as pd
import numpy as np
from pathlib import Path

CLEAN_FILE = Path("data/processed/matches_clean.csv")
OUTPUT = Path("data/processed/matches_featurized.csv")

ELO_K = 20
ELO_INIT = 1500


def verify_no_leakage(df):
    df_check = df.sort_values("Date").reset_index(drop=True)
    team_last_elo = {}
    team_history = {}
    result_map = {"H": 1, "D": 0, "A": -1}
    errors = 0
    for i, row in df_check.iterrows():
        home, away = row["HomeTeam"], row["AwayTeam"]
        date = row["Date"]
        ftr = row["FTR"]
        fthg = row["FTHG"]
        ftag = row["FTAG"]

        expected_home_elo = team_last_elo.get(home, ELO_INIT)
        expected_away_elo = team_last_elo.get(away, ELO_INIT)

        if not np.isclose(row["EloHome"], expected_home_elo, atol=1e-6):
            print(f"ELO-LEAK home {home}: row {i} date {date} has {row['EloHome']} expected {expected_home_elo}")
            errors += 1
        if not np.isclose(row["EloAway"], expected_away_elo, atol=1e-6):
            print(f"ELO-LEAK away {away}: row {i} date {date} has {row['EloAway']} expected {expected_away_elo}")
            errors += 1

        home_hist = team_history.get(home, [])
        away_hist = team_history.get(away, [])

        def form(hist, n):
            if len(hist) == 0:
                return np.nan
            recent = hist[-n:] if n < len(hist) else hist
            return np.mean([r["result"] for r in recent])

        def goals_avg(hist, n):
            if len(hist) == 0:
                return np.nan
            recent = hist[-n:] if n < len(hist) else hist
            return np.mean([r["gf"] for r in recent])

        def goals_conceded_avg(hist, n):
            if len(hist) == 0:
                return np.nan
            recent = hist[-n:] if n < len(hist) else hist
            return np.mean([r["ga"] for r in recent])

        checks = [
            ("HomeForm5", form(home_hist, 5)),
            ("HomeForm10", form(home_hist, 10)),
            ("AwayForm5", form(away_hist, 5)),
            ("AwayForm10", form(away_hist, 10)),
            ("HomeGoalsAvg5", goals_avg(home_hist, 5)),
            ("AwayGoalsAvg5", goals_avg(away_hist, 5)),
            ("HomeGoalsConcededAvg5", goals_conceded_avg(home_hist, 5)),
            ("AwayGoalsConcededAvg5", goals_conceded_avg(away_hist, 5)),
        ]
        for feat_name, expected_val in checks:
            actual = row[feat_name]
            if np.isnan(expected_val) and not np.isnan(actual):
                print(f"FORM-LEAK {feat_name}: row {i} expected NaN, got {actual}")
                errors += 1
            elif not np.isnan(expected_val) and not np.isclose(actual, expected_val, atol=1e-6):
                print(f"FORM-LEAK {feat_name}: row {i} date {date} has {actual} expected {expected_val}")
                errors += 1

        last_h2h = next((r for r in reversed(home_hist) if r["opponent"] == away), None)
        expected_h2h = last_h2h["result"] if last_h2h is not None else 0
        if row["H2HStreak"] != expected_h2h:
            print(f"H2H-LEAK: row {i} date {date} has {row['H2HStreak']} expected {expected_h2h}")
            errors += 1

        expected_home_rest = (date - home_hist[-1]["date"]).days if home_hist else np.nan
        expected_away_rest = (date - away_hist[-1]["date"]).days if away_hist else np.nan
        if not (np.isnan(expected_home_rest) and np.isnan(row["HomeRest"])) and \
           not np.isclose(row["HomeRest"], expected_home_rest, atol=1e-6):
            print(f"REST-LEAK home: row {i} has {row['HomeRest']} expected {expected_home_rest}")
            errors += 1
        if not (np.isnan(expected_away_rest) and np.isnan(row["AwayRest"])) and \
           not np.isclose(row["AwayRest"], expected_away_rest, atol=1e-6):
            print(f"REST-LEAK away: row {i} has {row['AwayRest']} expected {expected_away_rest}")
            errors += 1

        new_home_elo, new_away_elo = elo_update(expected_home_elo, expected_away_elo, ftr)
        team_last_elo[home] = new_home_elo
        team_last_elo[away] = new_away_elo

        match_result = result_map[ftr]
        team_history.setdefault(home, []).append(
            {"date": date, "result": match_result, "opponent": away, "gf": fthg, "ga": ftag}
        )
        team_history.setdefault(away, []).append(
            {"date": date, "result": -match_result, "opponent": home, "gf": ftag, "ga": fthg}
        )

    assert errors == 0, f"{errors} leakage violations detected"
    print("Leakage check PASSED: all features (Elo, form, goals, H2H, rest) computed from past data only")

def expected_score(rating_a, rating_b):
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

def elo_update(home_elo, away_elo, ftr):
    exp_h = expected_score(home_elo, away_elo)
    exp_a = 1 - exp_h
    if ftr == "H":
        score_h, score_a = 1, 0
    elif ftr == "A":
        score_h, score_a = 0, 1
    else:
        score_h, score_a = 0.5, 0.5
    new_home = home_elo + ELO_K * (score_h - exp_h)
    new_away = away_elo + ELO_K * (score_a - exp_a)
    return new_home, new_away

def main():
    df = pd.read_csv(CLEAN_FILE, low_memory=False)
    df["Date"] = pd.to_datetime(df["Date"])

    df = df.sort_values(["Date", "League", "HomeTeam"]).reset_index(drop=True)

    elo_dict = {}
    team_history = {}
    result_map = {"H": 1, "D": 0, "A": -1}

    home_elo_vals = np.empty(len(df), dtype=np.float64)
    away_elo_vals = np.empty(len(df), dtype=np.float64)
    home_form5 = np.empty(len(df), dtype=np.float64)
    home_form10 = np.empty(len(df), dtype=np.float64)
    away_form5 = np.empty(len(df), dtype=np.float64)
    away_form10 = np.empty(len(df), dtype=np.float64)
    h2h_streak = np.empty(len(df), dtype=np.int64)
    home_rest = np.empty(len(df), dtype=np.float64)
    away_rest = np.empty(len(df), dtype=np.float64)
    home_goals_avg5 = np.empty(len(df), dtype=np.float64)
    away_goals_avg5 = np.empty(len(df), dtype=np.float64)
    home_goals_conceded_avg5 = np.empty(len(df), dtype=np.float64)
    away_goals_conceded_avg5 = np.empty(len(df), dtype=np.float64)

    for i, row in df.iterrows():
        home = row["HomeTeam"]
        away = row["AwayTeam"]
        date = row["Date"]
        ftr = row["FTR"]
        fthg = row["FTHG"]
        ftag = row["FTAG"]

        home_elo = elo_dict.get(home, ELO_INIT)
        away_elo = elo_dict.get(away, ELO_INIT)
        home_elo_vals[i] = home_elo
        away_elo_vals[i] = away_elo

        home_hist = team_history.get(home, [])
        away_hist = team_history.get(away, [])

        def form(hist, n):
            if len(hist) == 0:
                return np.nan
            recent = hist[-n:] if n < len(hist) else hist
            return np.mean([r["result"] for r in recent])

        home_form5[i] = form(home_hist, 5)
        home_form10[i] = form(home_hist, 10)
        away_form5[i] = form(away_hist, 5)
        away_form10[i] = form(away_hist, 10)

        def goals_avg(hist, n):
            if len(hist) == 0:
                return np.nan
            recent = hist[-n:] if n < len(hist) else hist
            return np.mean([r["gf"] for r in recent])

        def goals_conceded_avg(hist, n):
            if len(hist) == 0:
                return np.nan
            recent = hist[-n:] if n < len(hist) else hist
            return np.mean([r["ga"] for r in recent])

        home_goals_avg5[i] = goals_avg(home_hist, 5)
        away_goals_avg5[i] = goals_avg(away_hist, 5)
        home_goals_conceded_avg5[i] = goals_conceded_avg(home_hist, 5)
        away_goals_conceded_avg5[i] = goals_conceded_avg(away_hist, 5)

        last_h2h = next(
            (
                r
                for r in reversed(home_hist)
                if r["opponent"] == away
            ),
            None,
        )
        if last_h2h is not None:
            h2h_streak[i] = last_h2h["result"]
        else:
            h2h_streak[i] = 0

        if home_hist:
            home_rest[i] = (date - home_hist[-1]["date"]).days
        else:
            home_rest[i] = np.nan

        if away_hist:
            away_rest[i] = (date - away_hist[-1]["date"]).days
        else:
            away_rest[i] = np.nan

        new_home_elo, new_away_elo = elo_update(home_elo, away_elo, ftr)
        elo_dict[home] = new_home_elo
        elo_dict[away] = new_away_elo

        match_result = result_map[ftr]
        team_history.setdefault(home, []).append(
            {
                "date": date,
                "result": match_result,
                "opponent": away,
                "gf": fthg,
                "ga": ftag,
            }
        )
        team_history.setdefault(away, []).append(
            {
                "date": date,
                "result": -match_result,
                "opponent": home,
                "gf": ftag,
                "ga": fthg,
            }
        )

    df["EloHome"] = home_elo_vals
    df["EloAway"] = away_elo_vals
    df["EloDiff"] = df["EloHome"] - df["EloAway"]
    df["HomeForm5"] = home_form5
    df["HomeForm10"] = home_form10
    df["AwayForm5"] = away_form5
    df["AwayForm10"] = away_form10
    df["H2HStreak"] = h2h_streak
    df["HomeRest"] = home_rest
    df["AwayRest"] = away_rest
    df["HomeGoalsAvg5"] = home_goals_avg5
    df["AwayGoalsAvg5"] = away_goals_avg5
    df["HomeGoalsConcededAvg5"] = home_goals_conceded_avg5
    df["AwayGoalsConcededAvg5"] = away_goals_conceded_avg5

    verify_no_leakage(df)

    df.to_csv(OUTPUT, index=False)
    print(f"Saved {len(df)} rows to {OUTPUT}")
    print(f"Feature columns: {[c for c in df.columns if c not in ['Date','HomeTeam','AwayTeam','FTHG','FTAG','FTR','Season','League','HomePoints','AwayPoints','B365H','B365D','B365A']]}")

if __name__ == "__main__":
    main()
