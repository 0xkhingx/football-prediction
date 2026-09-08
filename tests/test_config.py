"""Config + fair-play guards."""
from src.config import BANNED_ODDS_COLS, FEATURE_COLS_NO_ODDS, INV_TARGET_MAP, TARGET_MAP


def test_fair_play_feature_list():
    assert len(FEATURE_COLS_NO_ODDS) >= 23  # grows only via gated experiments
    assert len(set(FEATURE_COLS_NO_ODDS)) == len(FEATURE_COLS_NO_ODDS)


def test_no_overlap_with_banned_odds():
    assert not set(FEATURE_COLS_NO_ODDS) & set(BANNED_ODDS_COLS)


def test_target_map_roundtrip():
    assert set(TARGET_MAP) == {"H", "D", "A"}
    assert all(INV_TARGET_MAP[v] == k for k, v in TARGET_MAP.items())
