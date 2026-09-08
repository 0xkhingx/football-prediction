"""Season scoreboard: labeling, metric sanity, buckets, API contract.

Deliberately free of hardcoded counts/values: the record grows every
matchweek, so tests assert invariants and ranges, not snapshots.
"""
import pandas as pd

from src.score_live import BUCKETS, RECORD_FILE, metrics


def test_record_labels_valid():
    df = pd.read_csv(RECORD_FILE)
    assert len(df) > 0
    assert set(df.Source.unique()) <= {"backfill", "live"}


def test_tally_sane_ranges():
    df = pd.read_csv(RECORD_FILE)
    m = metrics(df)
    assert m["n"] == len(df)
    assert 0.0 <= m["acc"] <= 1.0
    assert 0.0 < m["log_loss"] < 2.0
    assert 0.0 <= m["brier"] <= 2.0


def test_buckets_cover_all_entries_and_match_spec():
    df = pd.read_csv(RECORD_FILE)
    m = metrics(df)
    assert [b["bucket"] for b in m["buckets"]] == [label for _, _, label in BUCKETS]
    assert sum(b["n"] for b in m["buckets"]) == len(df)
    for b in m["buckets"]:
        assert b["acc"] is None or 0.0 <= b["acc"] <= 1.0


def test_metrics_empty_frame():
    m = metrics(pd.DataFrame())
    assert m["n"] == 0 and m["acc"] is None


def test_api_season_record_contract():
    from fastapi.testclient import TestClient

    from api import app

    body = TestClient(app).get("/season-record").json()
    assert body["tally"]["n"] > 0
    assert 1 <= len(body["recent"]) <= 10
    assert "disclaimer" in body
