"""Date parsing must never day/month-swap ISO dates.

Regression test: clean.py once parsed '2025-11-01' as Jan 11 (dayfirst=True
on ISO input), silently corrupting chronology for whole seasons.
"""
import pandas as pd

from src.clean import parse_mixed_date


def test_iso_dates_parsed_exactly():
    assert parse_mixed_date("2025-11-01") == pd.Timestamp("2025-11-01")
    assert parse_mixed_date("2025-01-11") == pd.Timestamp("2025-01-11")
    assert parse_mixed_date("2026-05-04") == pd.Timestamp("2026-05-04")
    assert parse_mixed_date("2026-12-05") == pd.Timestamp("2026-12-05")


def test_legacy_slash_formats_still_work():
    assert parse_mixed_date("15/08/2015") == pd.Timestamp("2015-08-15")
    assert parse_mixed_date("01/02/16") == pd.Timestamp("2016-02-01")


def test_iso_never_swapped_bulk():
    dates = pd.Series(["2025-11-01", "2026-04-05", "2026-05-12", "2025-08-15"])
    parsed = dates.apply(parse_mixed_date)
    assert (parsed.dt.strftime("%Y-%m-%d") == dates).all()
