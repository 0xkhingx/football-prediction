import pandas as pd
import numpy as np
import requests
import json
from io import StringIO
from pathlib import Path
from datetime import datetime
import joblib

MODEL_DIR = Path("models")
OUTPUT_DIR = Path("data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = OUTPUT_DIR / "predictions_log.csv"

LEAGUE_NAMES = {
    "E0": "Premier League",
    "SP1": "La Liga",
    "I1": "Serie A",
    "D1": "Bundesliga",
    "F1": "Ligue 1",
}

FEATURE_COLS = [
    "EloHome", "EloAway", "EloDiff",
    "HomeForm5", "HomeForm10", "AwayForm5", "AwayForm10",
    "H2HStreak", "HomeRest", "AwayRest",
    "HomeGoalsAvg5", "AwayGoalsAvg5",
    "HomeGoalsConcededAvg5", "AwayGoalsConcededAvg5",
]

CLEAN_FILE = Path("data/processed/matches_clean.csv")
FEATURIZED_FILE = Path("data/processed/matches_featurized.csv")


def compute_features_for_fixture(row, elo_dict, team_history, result_map):
    home = row["HomeTeam"]
    away = row["AwayTeam"]
    date = pd.to_datetime(row["Date"], dayfirst=True)

    home_elo = elo_dict.get(home, 1500)
    away_elo = elo_dict.get(away, 1500)

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

    last_h2h = next((r for r in reversed(home_hist) if r["opponent"] == away), None)

    home_rest = (date - home_hist[-1]["date"]).days if home_hist else np.nan
    away_rest = (date - away_hist[-1]["date"]).days if away_hist else np.nan

    return {
        "EloHome": home_elo,
        "EloAway": away_elo,
        "EloDiff": home_elo - away_elo,
        "HomeForm5": form(home_hist, 5),
        "HomeForm10": form(home_hist, 10),
        "AwayForm5": form(away_hist, 5),
        "AwayForm10": form(away_hist, 10),
        "H2HStreak": last_h2h["result"] if last_h2h is not None else 0,
        "HomeRest": home_rest,
        "AwayRest": away_rest,
        "HomeGoalsAvg5": goals_avg(home_hist, 5),
        "AwayGoalsAvg5": goals_avg(away_hist, 5),
        "HomeGoalsConcededAvg5": goals_conceded_avg(home_hist, 5),
        "AwayGoalsConcededAvg5": goals_conceded_avg(away_hist, 5),
    }


def build_state_from_historical():
    df = pd.read_csv(CLEAN_FILE)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").reset_index(drop=True)

    elo_dict = {}
    team_history = {}
    result_map = {"H": 1, "D": 0, "A": -1}

    for _, row in df.iterrows():
        home = row["HomeTeam"]
        away = row["AwayTeam"]
        ftr = row["FTR"]
        fthg = row["FTHG"]
        ftag = row["FTAG"]

        home_elo = elo_dict.get(home, 1500)
        away_elo = elo_dict.get(away, 1500)

        def expected(rating_a, rating_b):
            return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

        exp_h = expected(home_elo, away_elo)
        exp_a = 1 - exp_h
        if ftr == "H":
            score_h, score_a = 1, 0
        elif ftr == "A":
            score_h, score_a = 0, 1
        else:
            score_h, score_a = 0.5, 0.5

        elo_dict[home] = home_elo + 20 * (score_h - exp_h)
        elo_dict[away] = away_elo + 20 * (score_a - exp_a)

        match_result = result_map[ftr]
        team_history.setdefault(home, []).append(
            {"date": row["Date"], "result": match_result, "opponent": away, "gf": fthg, "ga": ftag}
        )
        team_history.setdefault(away, []).append(
            {"date": row["Date"], "result": -match_result, "opponent": home, "gf": ftag, "ga": fthg}
        )

    return elo_dict, team_history, result_map


def fetch_fixtures():
    try:
        resp = requests.get("https://www.football-data.co.uk/fixtures.csv", timeout=15)
        if resp.status_code != 200:
            print(f"fixtures.csv returned HTTP {resp.status_code}")
            return pd.DataFrame()
        df = pd.read_csv(StringIO(resp.text))
        col_map = {}
        for c in df.columns:
            cleaned = c.replace("\ufeff", "").replace("\xef\xbb\xbf", "")
            cleaned = cleaned.replace("ï»¿", "")
            col_map[c] = cleaned
        df = df.rename(columns=col_map)

        if "Div" not in df.columns:
            print(f"Columns after cleaning: {list(df.columns)}")
            return pd.DataFrame()

        top_codes = ["E0", "SP1", "I1", "D1", "F1"]
        df = df[df["Div"].isin(top_codes)].copy()
        return df
    except Exception as e:
        print(f"Failed to fetch fixtures: {e}")
        return pd.DataFrame()


def main():
    print("=" * 60)
    print("LIVE FIXTURE PREDICTOR")
    print("=" * 60)

    fixtures = fetch_fixtures()
    if len(fixtures) == 0:
        # Try to find upcoming matches from current season CSVs
        print("No top-5-league fixtures on fixtures.csv.")
        print("Checking current season 2526 CSVs for unplayed matches...")
        for code in ["E0", "SP1", "I1", "D1", "F1"]:
            url = f"https://www.football-data.co.uk/mmz4281/2526/{code}.csv"
            try:
                resp = requests.get(url, timeout=15)
                if resp.status_code == 200:
                    df = pd.read_csv(StringIO(resp.text))
                    df["League"] = code
                    df.columns = df.columns.str.replace("\ufeff", "", regex=False)
                    unplayed = df[df["FTHG"].isna()]
                    if len(unplayed) > 0:
                        fixtures = pd.concat([fixtures, unplayed], ignore_index=True)
            except Exception as e:
                print(f"  {code}: {e}")
        if len(fixtures) == 0:
            print("\nNo upcoming fixtures found for top 5 leagues.")
            print("This is expected between seasons (July).")
            print("The predictor will work automatically when new fixtures appear.")
            return

    print(f"Found {len(fixtures)} upcoming fixtures")

    elo_dict, team_history, result_map = build_state_from_historical()

    imputer = joblib.load(MODEL_DIR / "imputer.joblib")
    scaler = joblib.load(MODEL_DIR / "scaler.joblib")
    lr = joblib.load(MODEL_DIR / "logistic_regression.joblib")
    xgb_model = joblib.load(MODEL_DIR / "xgboost.joblib")

    predictions = []
    for _, fixture in fixtures.iterrows():
        feats = compute_features_for_fixture(fixture, elo_dict, team_history, result_map)
        feat_array = np.array([[feats[c] for c in FEATURE_COLS]])
        feat_imp = imputer.transform(feat_array)
        feat_scaled = scaler.transform(feat_imp)

        xgb_probs = xgb_model.predict_proba(feat_imp)[0]
        lr_probs = lr.predict_proba(feat_scaled)[0]

        outcome = ["H", "D", "A"][np.argmax(xgb_probs)]
        confidence = np.max(xgb_probs)

        predictions.append({
            "Date": fixture["Date"],
            "League": fixture.get("League", fixture.get("Div", "?")),
            "Home": fixture["HomeTeam"],
            "Away": fixture["AwayTeam"],
            "Prediction": outcome,
            "Confidence": confidence,
            "P(H)": xgb_probs[0],
            "P(D)": xgb_probs[1],
            "P(A)": xgb_probs[2],
            "LR_P(H)": lr_probs[0],
        })

    pred_df = pd.DataFrame(predictions)
    pred_df = pred_df.sort_values("Date")

    print(f"\n{'Date':<14} {'League':<12} {'Home':<22} {'Away':<22} {'Pred':<6} {'Conf':<8} {'P(H)':<8} {'P(D)':<8} {'P(A)':<8}")
    print("-" * 106)
    for _, r in pred_df.iterrows():
        league_name = LEAGUE_NAMES.get(r["League"], r["League"])
        print(f"{str(r['Date']):<14} {league_name:<12} {r['Home']:<22} {r['Away']:<22} {r['Prediction']:<6} {r['Confidence']:<8.3f} {r['P(H)']:<8.3f} {r['P(D)']:<8.3f} {r['P(A)']:<8.3f}")

    if LOG_FILE.exists():
        existing = pd.read_csv(LOG_FILE)
        combined = pd.concat([existing, pred_df], ignore_index=True)
    else:
        combined = pred_df.copy()
    combined.to_csv(LOG_FILE, index=False)
    print(f"\nPredictions appended to {LOG_FILE}")
    print(f"Total logged predictions: {len(combined)}")


if __name__ == "__main__":
    main()
