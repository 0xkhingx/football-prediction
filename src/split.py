import pandas as pd
import numpy as np
from pathlib import Path
import json

FEATURIZED_FILE = Path("data/processed/matches_featurized.csv")
OUTPUT_DIR = Path("data/processed")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FEATURE_COLS = [
    "EloHome", "EloAway", "EloDiff",
    "EloHomeMargin", "EloAwayMargin", "EloDiffMargin",
    "HomeForm5", "HomeForm10", "AwayForm5", "AwayForm10",
    "H2HStreak", "HomeRest", "AwayRest",
    "HomeGoalsAvg5", "AwayGoalsAvg5",
    "HomeGoalsConcededAvg5", "AwayGoalsConcededAvg5",
    "HomeShotsAvg5", "AwayShotsAvg5",
    "HomeShotsOnTargetAvg5", "AwayShotsOnTargetAvg5",
    "HomeCornersAvg5", "AwayCornersAvg5",
]

TARGET = "FTR"
TARGET_MAP = {"H": 0, "D": 1, "A": 2}

def main():
    df = pd.read_csv(FEATURIZED_FILE, low_memory=False)
    df["Date"] = pd.to_datetime(df["Date"])

    df["target"] = df[TARGET].map(TARGET_MAP)

    seasons = sorted(df["Season"].unique())
    print(f"Seasons: {seasons}")

    test_season = seasons[-1]
    val_season = seasons[-2]
    train_seasons = seasons[:-2]

    train_mask = df["Season"].isin(train_seasons)
    val_mask = df["Season"] == val_season
    test_mask = df["Season"] == test_season

    X_train = df.loc[train_mask, FEATURE_COLS].copy()
    y_train = df.loc[train_mask, "target"].copy()
    X_val = df.loc[val_mask, FEATURE_COLS].copy()
    y_val = df.loc[val_mask, "target"].copy()
    X_test = df.loc[test_mask, FEATURE_COLS].copy()
    y_test = df.loc[test_mask, "target"].copy()

    dates_train = df.loc[train_mask, "Date"]
    dates_val = df.loc[val_mask, "Date"]
    dates_test = df.loc[test_mask, "Date"]

    meta = {
        "train_seasons": [int(s) for s in train_seasons],
        "val_season": int(val_season),
        "test_season": int(test_season),
        "train_size": len(X_train),
        "val_size": len(X_val),
        "test_size": len(X_test),
        "train_date_range": [str(dates_train.min().date()), str(dates_train.max().date())],
        "val_date_range": [str(dates_val.min().date()), str(dates_val.max().date())],
        "test_date_range": [str(dates_test.min().date()), str(dates_test.max().date())],
        "feature_cols": FEATURE_COLS,
        "target_map": TARGET_MAP,
    }
    print(json.dumps(meta, indent=2))

    np.savez_compressed(
        OUTPUT_DIR / "splits.npz",
        X_train=X_train.values.astype(np.float32),
        y_train=y_train.values.astype(np.int8),
        X_val=X_val.values.astype(np.float32),
        y_val=y_val.values.astype(np.int8),
        X_test=X_test.values.astype(np.float32),
        y_test=y_test.values.astype(np.int8),
    )

    with open(OUTPUT_DIR / "split_meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\nSaved splits to {OUTPUT_DIR / 'splits.npz'}")
    print(f"Train: {len(X_train)} | Val: {len(X_val)} | Test: {len(X_test)}")

if __name__ == "__main__":
    main()
