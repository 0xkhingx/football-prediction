"""Availability feed (Phase-1 stub) — free, fair-play, pre-match only.

openfootball/football.json carries no lineups (verified: matches have only
round/date/team1/team2/score), and football-data.co.uk has no injury data, so
there is no robust free automatic feed today. This module reserves the schema
so the harness can adopt availability without re-plumbing:

  data/availability_2627.csv columns:
    Date,League,Home,Away,HomeOut,AwayOut
    (counts of missing starters; 0 = full strength)

Behavior:
  - File absent -> all-NaN availability (AvailMissing=1), pipeline never fails.
  - File present -> validated (past dates only, known teams) and merged by
    features.py in a future pass. For now features.py emits the reserved
    all-NaN columns; this loader is the ingestion point.

Free manual sources that fit this schema (optional, weekly):
  - Club OS / league injury lists copied by hand before kickoff.
  - Any free pre-match sheet with "out" counts (never post-match xG).

Strictly no odds, no post-match info.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import FIXTURES_FILE

AVAIL_FILE = Path("data/availability_2627.csv")

EXPECTED_COLS = ["Date", "League", "Home", "Away", "HomeOut", "AwayOut"]


def load_availability(path: Path = AVAIL_FILE) -> pd.DataFrame:
    """Return validated availability frame, or empty frame if no feed."""
    if not path.exists():
        return pd.DataFrame(columns=EXPECTED_COLS)
    df = pd.read_csv(path)
    missing = [c for c in EXPECTED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"availability schema missing cols {missing}, want {EXPECTED_COLS}")
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    if df["Date"].isna().any():
        raise ValueError("availability has unparseable dates")
    for c in ("HomeOut", "AwayOut"):
        vals = pd.to_numeric(df[c], errors="coerce")
        if vals.isna().any() or (vals < 0).any():
            raise ValueError(f"availability {c} must be non-negative counts")
    return df[EXPECTED_COLS].copy()


def main() -> None:
    df = load_availability()
    if df.empty:
        print(f"No feed at {AVAIL_FILE} — features stay all-NaN (AvailMissing=1).")
        print("To add one, write Date,League,Home,Away,HomeOut,AwayOut rows for")
        print(f"fixtures in {FIXTURES_FILE} before kickoff.")
        return
    print(f"Loaded {len(df)} availability rows from {AVAIL_FILE}")
    print(f"Date range: {df['Date'].min().date()} to {df['Date'].max().date()}")


if __name__ == "__main__":
    main()
