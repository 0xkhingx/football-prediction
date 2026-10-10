"""Season scoreboard (Step 6) — tally only, no ROI.

Rebuilds data/season_record.csv from:
  1. backfill: single chronological sweep; every played 2026/27 match predicted
     point-in-time (state strictly before its date), labeled source=backfill;
  2. live: data/predictions_log.csv joined to completed matches, source=live
     (takes precedence over backfill for the same fixture).

Metrics: accuracy / log-loss / Brier overall + per league + per confidence
bucket. Run: python -m src.score_live
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import CLEAN_FILE, INV_TARGET_MAP, PREDICTIONS_LOG, RECORD_FILE
from .inference import (
    apply_calibrators,
    apply_honesty_gate,
    build_state_from_historical,
    featurize_fixture,
    load_artifacts,
    load_serving_stack,
    vectorize,
)

TARGET_SEASON = 2627
BUCKETS = [(0.70, 1.01, "70%+"), (0.60, 0.70, "60-70%"), (0.50, 0.60, "50-60%"),
           (0.45, 0.50, "45-50%"), (0.0, 0.45, "<45%")]


def _row_to_entry(date, league, home, away, probs, actual, source: str) -> dict:
    idx = int(np.argmax(probs))
    conf = float(np.max(probs))
    gate = apply_honesty_gate(probs)
    return {
        "Date": str(date.date() if hasattr(date, "date") else date),
        "League": league,
        "Home": home,
        "Away": away,
        "Prediction": INV_TARGET_MAP[idx],
        "Confidence": round(conf, 4),
        "PH": round(float(probs[0]), 4),
        "PD": round(float(probs[1]), 4),
        "PA": round(float(probs[2]), 4),
        "Actual": actual,
        "Correct": INV_TARGET_MAP[idx] == actual,
        "Call": gate["call"],
        "Source": source,
    }


def backfill() -> pd.DataFrame:
    imputer, model, name = load_artifacts()
    try:
        lr, scaler, weight, cal = load_serving_stack()
    except Exception:
        lr, scaler, weight, cal = None, None, 1.0, None
    print(f"backfilling with {name}" + (f" + blend(w={weight:.2f})+cal" if cal is not None else " (raw)"))
    entries: list[dict] = []

    def on_row(row, elo, melo, hist):
        if row["Season"] != TARGET_SEASON or pd.isna(row["FTR"]):
            return
        feats = featurize_fixture(row["HomeTeam"], row["AwayTeam"], row["Date"], elo, melo, hist)
        probs = model.predict_proba(imputer.transform(vectorize(feats)))[0]
        # Score the served path (blend + calibration), not raw XGB.
        if lr is not None and scaler is not None and weight < 1.0:
            try:
                lr_p = lr.predict_proba(scaler.transform(imputer.transform(vectorize(feats))))[0]
                probs = weight * probs + (1 - weight) * lr_p
            except Exception:
                pass
        if cal is not None:
            try:
                probs = apply_calibrators(probs.reshape(1, -1), cal)[0]
            except Exception:
                pass
        entries.append(_row_to_entry(row["Date"], row["League"], row["HomeTeam"],
                                     row["AwayTeam"], probs, row["FTR"], "backfill"))

    build_state_from_historical(on_row=on_row)
    df = pd.DataFrame(entries).sort_values("Date").reset_index(drop=True)
    print(f"backfilled {len(df)} played {TARGET_SEASON} matches")
    return df


def score_live_log() -> pd.DataFrame:
    if not PREDICTIONS_LOG.exists():
        return pd.DataFrame()
    log = pd.read_csv(PREDICTIONS_LOG)
    if log.empty:
        return log
    clean = pd.read_csv(CLEAN_FILE, low_memory=False)
    done = clean[clean.FTR.notna()][["Date", "League", "HomeTeam", "AwayTeam", "FTR"]]
    done["Date"] = pd.to_datetime(done["Date"]).dt.strftime("%Y-%m-%d")
    log["Date"] = pd.to_datetime(log["Date"]).dt.strftime("%Y-%m-%d")
    merged = log.merge(done, left_on=["Date", "League", "Home", "Away"],
                       right_on=["Date", "League", "HomeTeam", "AwayTeam"], how="inner")
    entries = []
    for _, r in merged.iterrows():
        probs = np.array([r["P(H)"], r["P(D)"], r["P(A)"]], dtype=float)
        e = _row_to_entry(r["Date"], r["League"], r["Home"], r["Away"], probs, r["FTR"], "live")
        # keep the originally logged call, not a recomputation
        e["Prediction"] = r["Prediction"]
        e["Confidence"] = float(r["Confidence"])
        e["Correct"] = r["Prediction"] == r["FTR"]
        entries.append(e)
    df = pd.DataFrame(entries)
    print(f"scored {len(df)} live logged calls")
    return df


def metrics(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"n": 0, "acc": None, "log_loss": None, "brier": None,
                "per_league": {},
                "buckets": [{"bucket": label, "n": 0, "acc": None} for _, _, label in BUCKETS]}
    y = df["Actual"].map({"H": 0, "D": 1, "A": 2}).to_numpy()
    p = df[["PH", "PD", "PA"]].to_numpy(dtype=float)
    p = np.clip(p, 1e-15, 1 - 1e-15)
    out = {
        "n": len(df),
        "acc": round(float((df["Prediction"] == df["Actual"]).mean()), 4),
        "log_loss": round(float(-np.mean([np.log(p[i, y[i]]) for i in range(len(df))])), 4),
        "brier": round(float(np.mean(((p - np.eye(3)[y]) ** 2).sum(axis=1))), 4),
    }
    by_league = {}
    for lg, sub in df.groupby("League"):
        ys = sub["Actual"].map({"H": 0, "D": 1, "A": 2}).to_numpy()
        ps = np.clip(sub[["PH", "PD", "PA"]].to_numpy(dtype=float), 1e-15, 1 - 1e-15)
        by_league[str(lg)] = {
            "n": len(sub),
            "acc": round(float((sub["Prediction"] == sub["Actual"]).mean()), 4),
            "log_loss": round(float(-np.mean([np.log(ps[i, ys[i]]) for i in range(len(sub))])), 4),
        }
    out["per_league"] = by_league
    buckets = []
    for lo, hi, label in BUCKETS:
        sub = df[(df.Confidence >= lo) & (df.Confidence < hi)]
        buckets.append({"bucket": label, "n": len(sub),
                        "acc": round(float((sub["Prediction"] == sub["Actual"]).mean()), 4) if len(sub) else None})
    out["buckets"] = buckets
    return out


def main():
    bf = backfill()
    live = score_live_log()
    if live.empty:
        combined = bf
    else:
        # Live real-time calls take precedence over backfilled replay.
        combined = pd.concat([bf, live], ignore_index=True)
        combined["_live"] = (combined.Source == "live").astype(int)
        combined = (combined.sort_values("_live")
                    .drop_duplicates(subset=["Date", "Home", "Away"], keep="last")
                    .drop(columns="_live").sort_values("Date").reset_index(drop=True))
    combined.to_csv(RECORD_FILE, index=False)
    m = metrics(combined)
    print(f"\nwrote {len(combined)} entries -> {RECORD_FILE}")
    print(f"tally: n={m['n']} acc={m['acc']} LL={m['log_loss']} brier={m['brier']}")
    for b in m["buckets"]:
        print(f"  {b['bucket']:>8}: n={b['n']:<5} acc={b['acc']}")


if __name__ == "__main__":
    main()
