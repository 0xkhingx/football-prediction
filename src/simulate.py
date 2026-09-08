"""Monte Carlo season simulator, v1 (Step 7).

For each league: current table from played 2627 matches + remaining fixtures
(from data/fixtures_2627.csv minus already-played), each remaining fixture
predicted ONCE with current state (probs frozen at current form — documented
approximation, not a chronological resim), then N seasons drawn vectorized.

Output: title/top-4 frequencies as ROUNDED BANDS (never false precision).
Run: python -m src.simulate  ->  data/simulation_2627.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .config import CLEAN_FILE
from .inference import build_state_from_historical, load_artifacts, predict_one

FIXTURES_FILE = Path("data/fixtures_2627.csv")
OUTPUT_FILE = Path("data/simulation_2627.json")
N_SIMS = 2000
SEED = 42
SEASON = 2627


def band(p: float) -> str:
    if p < 0.025:
        return "<5%"
    if p > 0.975:
        return ">95%"
    lo = int(p * 20) * 5
    return f"{lo}-{lo + 5}%"


def current_table(clean: pd.DataFrame, league: str) -> dict[str, int]:
    pts: dict[str, int] = {}
    sub = clean[(clean.Season == SEASON) & (clean.League == league) & clean.FTR.notna()]
    for _, r in sub.iterrows():
        h, a = r["HomeTeam"], r["AwayTeam"]
        pts.setdefault(h, 0)
        pts.setdefault(a, 0)
        if r["FTR"] == "H":
            pts[h] += 3
        elif r["FTR"] == "A":
            pts[a] += 3
        else:
            pts[h] += 1
            pts[a] += 1
    return pts


def rare_teams(clean: pd.DataFrame) -> set:
    """Mirror clean.py's rare-team rule so fixture names resolve to the same
    entities the model was trained/served on (e.g. Coventry -> Other)."""
    appearances = pd.concat([clean["HomeTeam"], clean["AwayTeam"]]).value_counts()
    return set(appearances[appearances < 3].index)


def remaining_fixtures(clean: pd.DataFrame, league: str) -> pd.DataFrame:
    played = set(zip(clean[(clean.Season == SEASON) & (clean.League == league)]["HomeTeam"],
                     clean[(clean.Season == SEASON) & (clean.League == league)]["AwayTeam"]))
    rare = rare_teams(clean)
    known = set(clean["HomeTeam"]) | set(clean["AwayTeam"])
    resolve = lambda t: t if (t in known and t not in rare) else "Other"
    fx = pd.read_csv(FIXTURES_FILE)
    fx = fx[fx.League == league].copy()
    fx["Home"] = fx["Home"].apply(resolve)
    fx["Away"] = fx["Away"].apply(resolve)
    fx = fx[~fx.apply(lambda r: (r["Home"], r["Away"]) in played, axis=1)]
    return fx.reset_index(drop=True)


def simulate_league(league: str, n_sims: int = N_SIMS, seed: int = SEED) -> dict:
    rng = np.random.default_rng(seed)
    clean = pd.read_csv(CLEAN_FILE, low_memory=False)
    table = current_table(clean, league)
    fx = remaining_fixtures(clean, league)
    for t in list(fx["Home"]) + list(fx["Away"]):
        table.setdefault(t, 0)
    print(f"{league}: {len(table)} teams, {len(fx)} remaining", flush=True)

    elo, melo, hist = build_state_from_historical()
    imputer, model, _ = load_artifacts()
    prob_rows = []
    for _, f in fx.iterrows():
        r = predict_one(f["Home"], f["Away"], f["Date"], elo, melo, hist, imputer, model,
                        league=league, with_scoreline=False)
        p = r["probabilities"]
        prob_rows.append((f["Home"], f["Away"], p["H"], p["D"], p["A"]))
    prob_rows = np.array(prob_rows, dtype=object) if prob_rows else np.empty((0, 5), dtype=object)

    teams = sorted(table)
    idx = {t: i for i, t in enumerate(teams)}
    base = np.array([table[t] for t in teams], dtype=float)
    titles = np.zeros(len(teams), dtype=int)
    top4s = np.zeros(len(teams), dtype=int)
    if len(prob_rows):
        ph = np.array([r[2] for r in prob_rows], dtype=float)
        pd_ = np.array([r[3] for r in prob_rows], dtype=float)
        home_idx = np.array([idx[r[0]] for r in prob_rows])
        away_idx = np.array([idx[r[1]] for r in prob_rows])
        draws = rng.random((n_sims, len(prob_rows)))
        # outcome: 0=H (draw < pH), 1=D (draw < pH+pD), else 2=A
        out = np.where(draws < ph, 0, np.where(draws < ph + pd_, 1, 2))
        hp = np.where(out == 0, 3.0, np.where(out == 1, 1.0, 0.0))
        ap = np.where(out == 2, 3.0, np.where(out == 1, 1.0, 0.0))
        add = np.zeros((n_sims, len(teams)))
        np.add.at(add, (np.arange(n_sims)[:, None], home_idx), hp)
        np.add.at(add, (np.arange(n_sims)[:, None], away_idx), ap)
        totals = base + add
        order = np.argsort(-totals, axis=1)
        for s in range(n_sims):
            titles[order[s, 0]] += 1
            for t in order[s, :4]:
                top4s[t] += 1
    table_out = [
        {"team": t, "pts": int(table[t]),
         "title": band(titles[i] / n_sims), "top4": band(top4s[i] / n_sims),
         "title_raw": round(float(titles[i] / n_sims), 4),
         "top4_raw": round(float(top4s[i] / n_sims), 4)}
        for i, t in enumerate(teams)
    ]
    table_out.sort(key=lambda r: -r["pts"])
    return {"league": league, "sims": n_sims, "table": table_out,
            "note": "Probs frozen at current form; bands rounded, not precise."}


def main():
    out = {"season": SEASON, "leagues": {}}
    for league in ["E0", "SP1", "I1", "D1", "F1"]:
        out["leagues"][league] = simulate_league(league)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(out, f, indent=2)
    print(f"saved {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
