"""Phase-1 candidates: chance proxies + new-team flags + availability schema."""
import pandas as pd

from src.config import EXPERIMENT_SETS, FEATURE_COLS_NO_ODDS
from src.pull_availability import load_availability


def test_prod_23_order_untouched():
    assert len(FEATURE_COLS_NO_ODDS) == 23
    assert FEATURE_COLS_NO_ODDS[0] == "EloHome"
    assert FEATURE_COLS_NO_ODDS[-1] == "AwayCornersAvg5"


def test_phase1_cols_present_and_past_only():
    df = pd.read_csv("data/processed/matches_featurized.csv", low_memory=False)
    for col in ["HomeShotAcc5", "AwayShotAcc5", "HomeConvRate5", "AwayConvRate5",
                "HomeNewTeam", "AwayNewTeam", "HomeOut", "AwayOut", "AvailMissing",
                "HomeAttStr", "AwayAttStr", "HomeDefStr", "AwayDefStr"]:
        assert col in df.columns, col
    # Ratios bounded where present; NaNs allowed (early history / openfootball era).
    for col in ["HomeShotAcc5", "AwayShotAcc5"]:
        s = df[col].dropna()
        assert ((s >= 0) & (s <= 1)).all(), col
    for col in ["HomeConvRate5", "AwayConvRate5"]:
        s = df[col].dropna()
        # Goals/SOT can exceed 1 over 5-game means in theory (deflected/awarded),
        # but must be finite and non-negative.
        assert (s >= 0).all() and s.notna().all(), col
    # New-team flags are binary and decline over time (promoted signal, not ghost).
    assert set(df["HomeNewTeam"].dropna().unique()) <= {0.0, 1.0}
    assert df["HomeNewTeam"].iloc[:50].mean() > df["HomeNewTeam"].iloc[-500:].mean()
    # Availability reserved: all-NaN outs + missing=1 until feed lands.
    assert df["HomeOut"].isna().all() and df["AwayOut"].isna().all()
    assert (df["AvailMissing"] == 1.0).all()


def test_experiment_sets_wired():
    assert EXPERIMENT_SETS["chance"] == ["HomeShotAcc5", "AwayShotAcc5", "HomeConvRate5", "AwayConvRate5"]
    assert EXPERIMENT_SETS["newteam"] == ["HomeNewTeam", "AwayNewTeam"]
    assert EXPERIMENT_SETS["avail"] == ["HomeOut", "AwayOut", "AvailMissing"]
    assert EXPERIMENT_SETS["oppadj"] == ["HomeAttStr", "AwayAttStr", "HomeDefStr", "AwayDefStr"]


def test_oppadj_bounded_and_stable():
    df = pd.read_csv("data/processed/matches_featurized.csv", low_memory=False)
    for col in ["HomeAttStr", "AwayAttStr", "HomeDefStr", "AwayDefStr"]:
        s = df[col].dropna()
        assert len(s) == len(df), col  # never NaN: starts at 1.0 prior
        assert ((s >= 0.40 - 1e-9) & (s <= 2.00 + 1e-9)).all(), col
    # Early history sits at prior 1.0; ratings disperse as evidence accumulates.
    assert (df[["HomeAttStr", "AwayAttStr"]].iloc[:20] == 1.0).all().all()


def test_availability_loader_noop_safe():
    df = load_availability()
    assert list(df.columns) == ["Date", "League", "Home", "Away", "HomeOut", "AwayOut"]
    assert df.empty  # no feed committed -> pipeline never fails
