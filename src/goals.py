"""Dixon-Coles scoreline probabilities (Step 5).

Time-weighted attack/defense strengths from FTHG/FTAG history, per league,
Poisson goal matrix with the Dixon-Coles low-score (rho) correction.
Strictly past-data-only: strengths use matches with Date < as_of.

Ship rule: scorelines surface only when the Poisson-implied outcome agrees
with the XGB call (consistency rule); otherwise null + reason.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

from .config import CLEAN_FILE
RHO = -0.13  # Dixon-Coles low-score dependence (literature estimate)
HALF_LIFE_DAYS = 270.0
MAX_GOALS = 7


from functools import lru_cache


@lru_cache(maxsize=1)
def cached_matches() -> pd.DataFrame:
    return load_matches()


@lru_cache(maxsize=1)
def team_league_map() -> dict:
    df = cached_matches()
    mode = df.groupby("HomeTeam")["League"].agg(lambda s: s.value_counts().index[0])
    return dict(mode)


def load_matches(clean_file: Path = CLEAN_FILE) -> pd.DataFrame:
    df = pd.read_csv(clean_file, low_memory=False)
    df["Date"] = pd.to_datetime(df["Date"])
    return df.sort_values("Date").reset_index(drop=True)


def _wmean(values: pd.Series, weights: np.ndarray) -> float:
    return float(np.average(values.to_numpy(dtype=float), weights=weights))


def team_strengths(df: pd.DataFrame, as_of, league: str) -> dict:
    """Weighted attack/defense ratings vs league averages. Past only."""
    as_of = pd.to_datetime(as_of)
    past = df[(df.League == league) & (df.Date < as_of)].reset_index(drop=True)
    if past.empty:
        raise ValueError(f"no history for {league} before {as_of}")
    w = (0.5 ** ((as_of - past["Date"]).dt.days.clip(lower=0).to_numpy(dtype=float) / HALF_LIFE_DAYS))
    home_avg = _wmean(past["FTHG"], w)
    away_avg = _wmean(past["FTAG"], w)

    def side(team_col: str, scored_col: str, conceded_col: str, avg_scored: float, avg_conceded: float):
        att, dfn = {}, {}
        for team, sub in past.groupby(team_col):
            sw = w[sub.index.to_numpy()]
            att[team] = _wmean(sub[scored_col], sw) / avg_scored
            dfn[team] = _wmean(sub[conceded_col], sw) / avg_conceded
        return att, dfn

    home_att, home_def = side("HomeTeam", "FTHG", "FTAG", home_avg, away_avg)
    away_att, away_def = side("AwayTeam", "FTAG", "FTHG", away_avg, home_avg)
    return {
        "home_avg": home_avg,
        "away_avg": away_avg,
        "home_att": home_att,
        "home_def": home_def,
        "away_att": away_att,
        "away_def": away_def,
    }


def _poisson(k: int, lam: float) -> float:
    return math.exp(-lam) * lam**k / math.factorial(k)


def _tau(h: int, a: int, lh: float, la: float) -> float:
    if h == 0 and a == 0:
        return 1 - lh * la * RHO
    if h == 0 and a == 1:
        return 1 + lh * RHO
    if h == 1 and a == 0:
        return 1 + la * RHO
    if h == 1 and a == 1:
        return 1 - RHO
    return 1.0


def predict_scorelines(home: str, away: str, league: str, as_of, df: pd.DataFrame | None = None) -> dict:
    if df is None:
        df = load_matches()
    s = team_strengths(df, as_of, league)
    lh = s["home_att"].get(home, 1.0) * s["away_def"].get(away, 1.0) * s["home_avg"]
    la = s["away_att"].get(away, 1.0) * s["home_def"].get(home, 1.0) * s["away_avg"]

    grid: dict[tuple[int, int], float] = {}
    for h in range(MAX_GOALS + 1):
        for a in range(MAX_GOALS + 1):
            grid[(h, a)] = _poisson(h, lh) * _poisson(a, la) * _tau(h, a, lh, la)
    total = sum(grid.values())
    grid = {k: v / total for k, v in grid.items()}

    pH = sum(p for (h, a), p in grid.items() if h > a)
    pD = sum(p for (h, a), p in grid.items() if h == a)
    pA = sum(p for (h, a), p in grid.items() if h < a)
    top = sorted(grid.items(), key=lambda kv: kv[1], reverse=True)[:3]
    by_outcome = {
        "H": sorted(((k, p) for k, p in grid.items() if k[0] > k[1]), key=lambda kv: kv[1], reverse=True),
        "D": sorted(((k, p) for k, p in grid.items() if k[0] == k[1]), key=lambda kv: kv[1], reverse=True),
        "A": sorted(((k, p) for k, p in grid.items() if k[0] < k[1]), key=lambda kv: kv[1], reverse=True),
    }
    outcome = "H" if pH >= max(pD, pA) else ("D" if pD >= pA else "A")
    return {
        "lambda_home": round(float(lh), 3),
        "lambda_away": round(float(la), 3),
        "pH": float(pH),
        "pD": float(pD),
        "pA": float(pA),
        "outcome": outcome,
        "top": [{"h": h, "a": a, "p": round(float(p), 4)} for (h, a), p in top],
        "conditional": {
            o: [{"h": h, "a": a, "p": round(float(p), 4)} for (h, a), p in lst[:2]]
            for o, lst in by_outcome.items()
        },
    }


def select_scoreline(sc: dict, xgb_prediction: str, gate_call: bool) -> dict:
    """Pick the scoreline to stamp. Conditional-on-XGB by construction, so a
    stamped scoreline can never contradict the call — no suppression UX needed.
    """
    if not gate_call:
        return {"shown": False, "reason": "XGB too close to call — no scoreline stamped"}
    cond = sc["conditional"].get(xgb_prediction, [])
    if not cond:
        return {"shown": False, "reason": "no scoreline for this outcome"}
    top_pick = cond[0]
    return {
        "shown": True,
        "h": top_pick["h"],
        "a": top_pick["a"],
        "p": top_pick["p"],
        "reason": f"most likely {xgb_prediction} scoreline (Poisson, conditional on XGB call)",
    }


def consistent_with_xgb(scoreline_outcome: str, xgb_prediction: str, gate_call: bool) -> tuple[bool, str]:
    if not gate_call:
        return False, "XGB too close to call — no scoreline stamped"
    if scoreline_outcome != xgb_prediction:
        return (
            False,
            f"model conflict (Poisson {scoreline_outcome} vs XGB {xgb_prediction}) — no scoreline stamped",
        )
    return True, "Poisson and XGB agree"
