"""Train/serve parity: inference features must match training features.

Replays clean history strictly before a mid-history match, featurizes it,
and compares against data/processed/matches_featurized.csv.
"""
import numpy as np
import pandas as pd

from src.config import CLEAN_FILE, ELO_INIT, ELO_K, FEATURIZED_FILE, FEATURE_COLS_NO_ODDS
from src.features import elo_update, expected_score, margin_actual_score
from src.inference import featurize_fixture


def _replay_state_before(df_clean, pos):
    elo: dict = {}
    melo: dict = {}
    hist: dict = {}
    rmap = {"H": 1, "D": 0, "A": -1}
    for _, row in df_clean.iloc[:pos].iterrows():
        home, away, ftr = row["HomeTeam"], row["AwayTeam"], row["FTR"]
        he, ae = elo.get(home, ELO_INIT), elo.get(away, ELO_INIT)
        elo[home], elo[away] = elo_update(he, ae, ftr)
        mh, ma = melo.get(home, ELO_INIT), melo.get(away, ELO_INIT)
        sh, sa = margin_actual_score(row["FTHG"], row["FTAG"])
        exp = expected_score(mh, ma)
        melo[home] = mh + ELO_K * (sh - exp)
        melo[away] = ma + ELO_K * (sa - (1 - exp))
        m = rmap[ftr]
        hist.setdefault(home, []).append(
            {"date": row["Date"], "result": m, "opponent": away,
             "gf": row["FTHG"], "ga": row["FTAG"],
             "hs": row.get("HS", np.nan), "as": row.get("AS", np.nan),
             "hst": row.get("HST", np.nan), "ast": row.get("AST", np.nan),
             "hc": row.get("HC", np.nan), "ac": row.get("AC", np.nan)}
        )
        hist.setdefault(away, []).append(
            {"date": row["Date"], "result": -m, "opponent": home,
             "gf": row["FTAG"], "ga": row["FTHG"],
             "hs": row.get("AS", np.nan), "as": row.get("HS", np.nan),
             "hst": row.get("AST", np.nan), "ast": row.get("HST", np.nan),
             "hc": row.get("AC", np.nan), "ac": row.get("HC", np.nan)}
        )
    return elo, melo, hist


def _close(a, b):
    if pd.isna(a) and pd.isna(b):
        return True
    if pd.isna(a) or pd.isna(b):
        return False
    return abs(float(a) - float(b)) < 1e-4


def test_point_in_time_parity():
    clean = pd.read_csv(CLEAN_FILE, low_memory=False)
    clean["Date"] = pd.to_datetime(clean["Date"])
    clean = clean.sort_values(["Date", "League", "HomeTeam"]).reset_index(drop=True)
    feat = pd.read_csv(FEATURIZED_FILE, low_memory=False)

    # Same sort as features.py main: match rows by (Date, League, HomeTeam, AwayTeam).
    feat["Date"] = pd.to_datetime(feat["Date"])
    feat_sorted = feat.sort_values(["Date", "League", "HomeTeam"]).reset_index(drop=True)

    n = len(feat_sorted)
    positions = sorted({1000, n // 3, 2 * n // 3} - {0})
    positions = [p for p in positions if p < n]
    assert len(positions) >= 2  # meaningful spread across history
    for pos in positions:
        target = feat_sorted.iloc[pos]
        # Locate same match in clean frame.
        mask = (
            (clean["Date"] == target["Date"])
            & (clean["League"] == target["League"])
            & (clean["HomeTeam"] == target["HomeTeam"])
            & (clean["AwayTeam"] == target["AwayTeam"])
        )
        assert mask.sum() == 1, f"match not unique at pos {pos}"
        clean_pos = int(mask[mask].index[0])
        elo, melo, hist = _replay_state_before(clean, clean_pos)
        f = featurize_fixture(
            target["HomeTeam"], target["AwayTeam"], target["Date"], elo, melo, hist
        )
        assert list(f.keys()) == FEATURE_COLS_NO_ODDS
        mismatches = [c for c in FEATURE_COLS_NO_ODDS if not _close(f[c], target[c])]
        assert not mismatches, f"pos {pos} mismatch: {mismatches}"
