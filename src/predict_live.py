"""Live fixture predictor — fair-play XGB-tuned, no odds.

Uses src.config + src.inference (single source of truth).
Log dedupes on (Date, Home, Away).
"""
from __future__ import annotations

from io import StringIO

import pandas as pd
import requests

from .config import FIXTURES_FILE as LOCAL_FIXTURES
from .config import LEAGUE_NAMES, PREDICTIONS_LOG, TOP_LEAGUE_CODES
from .inference import build_state_from_historical, load_artifacts, predict_one


def current_season_code(today=None) -> str:
    """Football season code for a date: Aug-Dec -> YY(YY+1), Jan-Jul -> (YY-1)YY."""
    today = pd.to_datetime(today) if today is not None else pd.Timestamp.today()
    y = today.year % 100
    return f"{y}{y + 1}" if today.month >= 7 else f"{y - 1:02d}{y:02d}"


def fetch_local_fixtures() -> pd.DataFrame:
    """Upcoming fixtures from the local fixtures file (written by pull_openfootball)."""
    if not LOCAL_FIXTURES.exists():
        return pd.DataFrame()
    fx = pd.read_csv(LOCAL_FIXTURES)
    fx["Date"] = pd.to_datetime(fx["Date"], errors="coerce")
    today = pd.Timestamp.today().normalize()
    fx = fx[fx["Date"] >= today].copy()
    if fx.empty:
        return fx
    if "Round" not in fx.columns:
        fx["Round"] = ""
    return pd.DataFrame({
        "Div": fx["League"],
        "HomeTeam": fx["Home"],
        "AwayTeam": fx["Away"],
        "Date": fx["Date"].dt.strftime("%Y-%m-%d"),
        "Round": fx["Round"].fillna("").astype(str),
    }).reset_index(drop=True)


def fetch_fixtures() -> pd.DataFrame:
    """Network first, local fixtures file second.

    Result carries df.attrs["source"] = live|local|none and
    df.attrs["network_ok"] so callers can tell outage from offseason.
    """
    network_ok = False
    try:
        resp = requests.get("https://www.football-data.co.uk/fixtures.csv", timeout=15)
        if resp.status_code != 200:
            print(f"fixtures.csv returned HTTP {resp.status_code}")
        else:
            network_ok = True
            df = pd.read_csv(StringIO(resp.text))
            col_map = {}
            for c in df.columns:
                cleaned = c.replace("\ufeff", "").replace("\xef\xbb\xbf", "")
                cleaned = cleaned.replace("ï»¿", "")
                col_map[c] = cleaned
            df = df.rename(columns=col_map)

            if "Div" not in df.columns:
                print(f"Columns after cleaning: {list(df.columns)}")
            else:
                df = df[df["Div"].isin(TOP_LEAGUE_CODES)].copy()
                if len(df):
                    print(f"fixtures source: live ({len(df)} rows)")
                    df.attrs["source"] = "live"
                    df.attrs["network_ok"] = True
                    return df
    except Exception as e:  # noqa: BLE001 — any fetch failure falls back to local cache
        print(f"Failed to fetch fixtures: {e}")
    local = fetch_local_fixtures()
    if len(local):
        print(f"fixtures source: local cache ({len(local)} upcoming)")
        local.attrs["source"] = "local"
    else:
        local.attrs["source"] = "none"
    local.attrs["network_ok"] = network_ok
    return local


def _fallback_current_season() -> pd.DataFrame:
    season = current_season_code()
    fixtures = pd.DataFrame()
    for code in TOP_LEAGUE_CODES:
        url = f"https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                df = pd.read_csv(StringIO(resp.text))
                df["League"] = code
                df.columns = df.columns.str.replace("\ufeff", "", regex=False)
                unplayed = df[df["FTHG"].isna()]
                if len(unplayed) > 0:
                    fixtures = pd.concat([fixtures, unplayed], ignore_index=True)
        except Exception as e:  # noqa: BLE001 — one bad league must not kill the other four
            print(f"  {code}: {e}")
    return fixtures


def main() -> None:
    print("=" * 60)
    print("LIVE FIXTURE PREDICTOR (fair-play XGB-tuned)")
    print("=" * 60)

    fixtures = fetch_fixtures()
    if len(fixtures) == 0:
        print("No top-5-league fixtures on fixtures.csv.")
        print(f"Checking current season {current_season_code()} CSVs for unplayed matches...")
        fixtures = _fallback_current_season()
        if len(fixtures) == 0:
            print("\nNo upcoming fixtures found for top 5 leagues.")
            print("This is expected between seasons (July).")
            print("The predictor will work automatically when new fixtures appear.")
            return

    print(f"Found {len(fixtures)} upcoming fixtures")

    elo, margin_elo, team_history = build_state_from_historical()
    imputer, model, model_file = load_artifacts()
    print(f"Model: {model_file}")

    predictions = []
    for _, fixture in fixtures.iterrows():
        home = fixture["HomeTeam"]
        away = fixture["AwayTeam"]
        try:
            r = predict_one(home, away, fixture["Date"], elo, margin_elo, team_history, imputer, model,
                            league=fixture.get("League", fixture.get("Div")))
        except Exception as e:  # noqa: BLE001 — skip bad fixture, keep the batch going
            print(f"  skip {home} vs {away}: {e}")
            continue
        p = r["probabilities"]
        predictions.append(
            {
                "Date": fixture["Date"],
                "League": fixture.get("League", fixture.get("Div", "?")),
                "Home": home,
                "Away": away,
                "Prediction": r["prediction"],
                "Confidence": r["confidence"],
                "P(H)": p["H"],
                "P(D)": p["D"],
                "P(A)": p["A"],
                "Call": r["gate"]["call"],
                "CallLabel": r["gate"]["label"],
            }
        )

    if not predictions:
        print("No fixtures predicted.")
        return

    pred_df = pd.DataFrame(predictions).sort_values("Date")

    print(f"\n{'Date':<14} {'League':<12} {'Home':<22} {'Away':<22} {'Pred':<6} {'Conf':<8} {'P(H)':<8} {'P(D)':<8} {'P(A)':<8} {'Call'}")
    print("-" * 120)
    for _, r in pred_df.iterrows():
        league_name = LEAGUE_NAMES.get(r["League"], r["League"])
        gate = "CALL" if r["Call"] else "no-call"
        print(f"{r['Date']!s:<14} {league_name:<12} {r['Home']:<22} {r['Away']:<22} {r['Prediction']:<6} {r['Confidence']:<8.3f} {r['P(H)']:<8.3f} {r['P(D)']:<8.3f} {r['P(A)']:<8.3f} {gate}")

    PREDICTIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
    append_predictions(pred_df)
    print(f"\nPredictions written to {PREDICTIONS_LOG} (deduped)")
    print(f"Total logged predictions: {len(pd.read_csv(PREDICTIONS_LOG))}")


def append_predictions(pred_df: pd.DataFrame) -> pd.DataFrame:
    """Append new predictions to the log. LOGGED ROWS ARE IMMUTABLE:
    keep="first" so re-running after matches are played can never rewrite
    the originally logged call (the scoreboard treats the log as the
    authoritative real-time record).
    """
    PREDICTIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
    if PREDICTIONS_LOG.exists():
        existing = pd.read_csv(PREDICTIONS_LOG)
        # Forward-compatible schema: old logs lack Call columns.
        for col, default in (("Call", True), ("CallLabel", "")):
            if col not in existing.columns:
                existing[col] = default
        combined = pd.concat([existing, pred_df], ignore_index=True)
        combined = combined.drop_duplicates(subset=["Date", "Home", "Away"], keep="first")
    else:
        combined = pred_df.copy()
    combined.to_csv(PREDICTIONS_LOG, index=False)
    return combined


if __name__ == "__main__":
    main()
