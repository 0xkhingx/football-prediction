"""Shared inference — used by CLI, FastAPI, and (indirectly) Next.js.

Fair-play only: never touches B365 / ProbB365* columns.
Feature logic mirrors src/features.py so train == serve.
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from .config import (
    BANNED_ODDS_COLS,
    CLEAN_FILE,
    ELO_INIT,
    ELO_K,
    FEATURE_COLS_NO_ODDS,
    INV_TARGET_MAP,
    MIN_CONFIDENCE,
    MODEL_DIR,
    PROD_IMPUTER_NAME,
    PROD_MODEL_NAME,
    REGISTRY_FILE,
)
from .features import elo_update, expected_score, margin_actual_score


def guard_no_odds(payload: dict) -> None:
    leaked = [c for c in BANNED_ODDS_COLS if c in payload]
    if leaked:
        raise ValueError(f"fair-play violation: odds cols in payload {leaked}")


def load_registry(path: Path = REGISTRY_FILE) -> dict | None:
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def load_artifacts(model_dir: Path = MODEL_DIR):
    """Load prod imputer + XGB model.

    Registry present -> pinned files MUST exist (fail loud; never serve
    weaker weights under prod metrics). No registry (dev) -> conventional
    prod filenames, no silent downgrade to legacy artifacts.
    """
    reg = load_registry()
    if reg:
        model_file = model_dir / f"{reg['model_name']}.joblib"
        imputer_file = model_dir / f"{reg['imputer_name']}.joblib"
        missing = [p for p in (model_file, imputer_file) if not p.exists()]
        if missing:
            raise FileNotFoundError(
                f"registry-pinned artifacts missing: {missing}. "
                f"Run python -m src.train_tuned_prod to rebuild."
            )
    else:
        model_file = model_dir / f"{PROD_MODEL_NAME}.joblib"
        imputer_file = model_dir / f"{PROD_IMPUTER_NAME}.joblib"
        missing = [p for p in (model_file, imputer_file) if not p.exists()]
        if missing:
            raise FileNotFoundError(
                f"prod artifacts missing (no registry to fall back on): {missing}."
            )

    imputer = joblib.load(imputer_file)
    model = joblib.load(model_file)
    return imputer, model, str(model_file.name)


def _mean(xs: list) -> float:
    return float(np.mean(xs)) if xs else float("nan")


def build_state_from_historical(clean_file: Path = CLEAN_FILE, on_row=None):
    """Replay clean history -> (elo, margin_elo, team_history).

    Mirrors src/features.py main loop, including shots/corners history
    (predict_live.py dropped these — that was part of the skew).

    on_row(row, elo, margin_elo, team_history), if given, fires BEFORE each
    row is folded into state — lets callers (scoreboard backfill) predict
    point-in-time without a second replay implementation to drift.
    """
    df = pd.read_csv(clean_file, low_memory=False)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values(["Date", "League", "HomeTeam"]).reset_index(drop=True)

    elo: dict[str, float] = {}
    margin_elo: dict[str, float] = {}
    team_history: dict[str, list[dict]] = {}
    result_map = {"H": 1, "D": 0, "A": -1}

    for _, row in df.iterrows():
        if on_row is not None:
            on_row(row, elo, margin_elo, team_history)
        home, away = row["HomeTeam"], row["AwayTeam"]
        ftr = row["FTR"]

        home_elo = elo.get(home, ELO_INIT)
        away_elo = elo.get(away, ELO_INIT)
        new_home_elo, new_away_elo = elo_update(home_elo, away_elo, ftr)
        elo[home], elo[away] = new_home_elo, new_away_elo

        m_home = margin_elo.get(home, ELO_INIT)
        m_away = margin_elo.get(away, ELO_INIT)
        margin_h, margin_a = margin_actual_score(row["FTHG"], row["FTAG"])
        exp_h = expected_score(m_home, m_away)
        margin_elo[home] = m_home + ELO_K * (margin_h - exp_h)
        margin_elo[away] = m_away + ELO_K * (margin_a - (1 - exp_h))

        m = result_map[ftr]
        team_history.setdefault(home, []).append(
            {
                "date": row["Date"],
                "result": m,
                "opponent": away,
                "gf": row["FTHG"],
                "ga": row["FTAG"],
                "hs": row.get("HS", np.nan),
                "as": row.get("AS", np.nan),
                "hst": row.get("HST", np.nan),
                "ast": row.get("AST", np.nan),
                "hc": row.get("HC", np.nan),
                "ac": row.get("AC", np.nan),
            }
        )
        team_history.setdefault(away, []).append(
            {
                "date": row["Date"],
                "result": -m,
                "opponent": home,
                "gf": row["FTAG"],
                "ga": row["FTHG"],
                "hs": row.get("AS", np.nan),
                "as": row.get("HS", np.nan),
                "hst": row.get("AST", np.nan),
                "ast": row.get("HST", np.nan),
                "hc": row.get("AC", np.nan),
                "ac": row.get("HC", np.nan),
            }
        )

    return elo, margin_elo, team_history


def featurize_fixture(home: str, away: str, date, elo, margin_elo, team_history) -> dict:
    """Compute the 23 fair-play features for one fixture."""
    date = pd.to_datetime(date)
    home_elo = elo.get(home, ELO_INIT)
    away_elo = elo.get(away, ELO_INIT)
    home_hist = team_history.get(home, [])
    away_hist = team_history.get(away, [])

    def form(hist, n):
        if not hist:
            return float("nan")
        recent = hist[-n:]
        return float(np.mean([r["result"] for r in recent]))

    def avg(hist, key, n=5):
        # Mirror src/features.py exactly: NaN propagates (imputer handles it).
        if not hist:
            return float("nan")
        recent = hist[-n:]
        return float(np.mean([r[key] for r in recent]))

    last_h2h = next((r for r in reversed(home_hist) if r["opponent"] == away), None)

    feats = {
        "EloHome": float(home_elo),
        "EloAway": float(away_elo),
        "EloDiff": float(home_elo - away_elo),
        "EloHomeMargin": float(margin_elo.get(home, ELO_INIT)),
        "EloAwayMargin": float(margin_elo.get(away, ELO_INIT)),
        "EloDiffMargin": float(margin_elo.get(home, ELO_INIT) - margin_elo.get(away, ELO_INIT)),
        "HomeForm5": form(home_hist, 5),
        "HomeForm10": form(home_hist, 10),
        "AwayForm5": form(away_hist, 5),
        "AwayForm10": form(away_hist, 10),
        "H2HStreak": int(last_h2h["result"]) if last_h2h is not None else 0,
        "HomeRest": float((date - home_hist[-1]["date"]).days) if home_hist else float("nan"),
        "AwayRest": float((date - away_hist[-1]["date"]).days) if away_hist else float("nan"),
        "HomeGoalsAvg5": avg(home_hist, "gf"),
        "AwayGoalsAvg5": avg(away_hist, "gf"),
        "HomeGoalsConcededAvg5": avg(home_hist, "ga"),
        "AwayGoalsConcededAvg5": avg(away_hist, "ga"),
        "HomeShotsAvg5": avg(home_hist, "hs"),
        "AwayShotsAvg5": avg(away_hist, "as"),
        "HomeShotsOnTargetAvg5": avg(home_hist, "hst"),
        "AwayShotsOnTargetAvg5": avg(away_hist, "ast"),
        "HomeCornersAvg5": avg(home_hist, "hc"),
        "AwayCornersAvg5": avg(away_hist, "ac"),
    }

    guard_no_odds(feats)
    if list(feats.keys()) != FEATURE_COLS_NO_ODDS:
        raise ValueError("feature order drift vs config")
    return feats


def vectorize(feats: dict) -> np.ndarray:
    guard_no_odds(feats)
    return np.array([[feats[c] for c in FEATURE_COLS_NO_ODDS]], dtype=np.float32)


def form_badges(team_history, team: str, n: int = 5) -> list[str]:
    """Last-n results from the team's own perspective (oldest first)."""
    hist = team_history.get(team, [])
    mapping = {1: "W", 0: "D", -1: "L"}
    return [mapping.get(r["result"], "?") for r in hist[-n:]]


def last_meeting(team_history, home: str, away: str) -> dict | None:
    """Most recent meeting between the two, oriented as home vs away."""
    best = None
    for team in (home, away):
        for r in team_history.get(team, []):
            if r["opponent"] == (away if team == home else home):
                if best is None or r["date"] > best[0]:
                    best = (r["date"], team, r)
    if best is None:
        return None
    _, entry_team, r = best
    if entry_team == home:
        hg, ag = r["gf"], r["ga"]
    else:
        hg, ag = r["ga"], r["gf"]
    return {
        "date": str(r["date"].date() if hasattr(r["date"], "date") else r["date"]),
        "home_goals": int(hg),
        "away_goals": int(ag),
    }


def predict_one(home: str, away: str, date, elo, margin_elo, team_history, imputer, model,
                league: str | None = None, with_scoreline: bool = True) -> dict:
    feats = featurize_fixture(home, away, date, elo, margin_elo, team_history)
    x = vectorize(feats)
    probs = model.predict_proba(imputer.transform(x))[0]
    idx = int(np.argmax(probs))
    gate = apply_honesty_gate(probs)
    scoreline = score_for_fixture(home, away, date, league, INV_TARGET_MAP[idx], gate["call"]) if with_scoreline else None
    return {
        "home": home,
        "away": away,
        "probabilities": {"H": float(probs[0]), "D": float(probs[1]), "A": float(probs[2])},
        "prediction": INV_TARGET_MAP[idx],
        "confidence": float(np.max(probs)),
        "gate": gate,
        "form": {home: form_badges(team_history, home), away: form_badges(team_history, away)},
        "h2h": last_meeting(team_history, home, away),
        "scoreline": scoreline,
        "features": feats,
    }


def score_for_fixture(home: str, away: str, date, league: str | None,
                      xgb_prediction: str, gate_call: bool) -> dict | None:
    """Dixon-Coles scoreline pick, conditional on the XGB call. None when the
    league can't be resolved (manual entry of unknown teams)."""
    from .goals import cached_matches, predict_scorelines, select_scoreline, team_league_map

    lg = league or team_league_map().get(home) or team_league_map().get(away)
    if lg is None:
        return None
    try:
        sc = predict_scorelines(home, away, lg, date, cached_matches())
    except ValueError:
        return None
    return select_scoreline(sc, xgb_prediction, gate_call)


def apply_honesty_gate(probs) -> dict:
    """Step-3 honesty gate: stamp a call only at/above MIN_CONFIDENCE."""
    probs = np.asarray(probs, dtype=float)
    idx = int(np.argmax(probs))
    confidence = float(np.max(probs))
    call = confidence >= MIN_CONFIDENCE
    return {
        "call": bool(call),
        "label": f"MODEL CALLS {INV_TARGET_MAP[idx]}" if call else "TOO CLOSE TO CALL",
        "threshold": MIN_CONFIDENCE,
    }
