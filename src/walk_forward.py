import numpy as np
import pandas as pd
import json
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

FEATURIZED_FILE = Path("data/processed/matches_featurized.csv")
OUTPUT_DIR = Path("data/processed")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FEATURE_COLS_NO_ODDS = [
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
FEATURE_COLS_WITH_ODDS = FEATURE_COLS_NO_ODDS + ["ProbB365H", "ProbB365D", "ProbB365A"]

TARGET_MAP = {"H": 0, "D": 1, "A": 2}


def log_loss(y_true, y_pred_proba, eps=1e-15):
    y_pred_proba = np.clip(y_pred_proba, eps, 1 - eps)
    n = len(y_true)
    loss = 0.0
    for i in range(n):
        loss -= np.log(y_pred_proba[i, y_true[i]])
    return loss / n


def train_lr(X_train, y_train, X_test):
    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()
    X_train_imp = imputer.fit_transform(X_train)
    X_train_scaled = scaler.fit_transform(X_train_imp)
    lr = LogisticRegression(max_iter=5000, random_state=42)
    lr.fit(X_train_scaled, y_train)
    X_test_imp = imputer.transform(X_test)
    X_test_scaled = scaler.transform(X_test_imp)
    return lr.predict_proba(X_test_scaled)


def main():
    df = pd.read_csv(FEATURIZED_FILE, low_memory=False)
    df["Date"] = pd.to_datetime(df["Date"])
    df["target"] = df["FTR"].map(TARGET_MAP)
    odds_available = all(c in df.columns for c in ["ProbB365H", "ProbB365D", "ProbB365A"])

    seasons = sorted(df["Season"].unique())

    rows = []
    for i in range(1, len(seasons)):
        train_seasons = seasons[:i]
        test_season = seasons[i]

        train_mask = df["Season"].isin(train_seasons)
        test_mask = df["Season"] == test_season

        # Determine B365-valid subset (same rows for all models)
        test_df = df[test_mask]
        has_b365 = test_df["B365H"].notna() & test_df["B365D"].notna() & test_df["B365A"].notna()
        valid_counts = int(has_b365.sum())
        total_counts = int(len(test_df))

        y_train = df.loc[train_mask, "target"].values
        y_test_all = df.loc[test_mask, "target"].values
        y_test = y_test_all[has_b365.values] if valid_counts < total_counts else y_test_all

        # No-odds
        X_train = df.loc[train_mask, FEATURE_COLS_NO_ODDS].values
        X_test_all = df.loc[test_mask, FEATURE_COLS_NO_ODDS].values
        lr_no_probs = train_lr(X_train, y_train, X_test_all)
        lr_no_ll = log_loss(y_test, lr_no_probs[has_b365.values] if valid_counts < total_counts else lr_no_probs)

        # With-odds
        lr_with_ll = None
        if odds_available:
            X_train_o = df.loc[train_mask, FEATURE_COLS_WITH_ODDS].values
            X_test_o_all = df.loc[test_mask, FEATURE_COLS_WITH_ODDS].values
            lr_with_probs = train_lr(X_train_o, y_train, X_test_o_all)
            lr_with_ll = log_loss(y_test, lr_with_probs[has_b365.values] if valid_counts < total_counts else lr_with_probs)

        # Bookmaker
        book_ll = None
        if valid_counts > 10:
            book_raw = np.column_stack([
                1 / test_df.loc[has_b365, c].values for c in ["B365H", "B365D", "B365A"]
            ])
            book_probs = book_raw / book_raw.sum(axis=1, keepdims=True)
            book_ll = log_loss(y_test, book_probs)

        rows.append({
            "test_season": int(test_season),
            "n_train": int(len(y_train)),
            "n_test": int(valid_counts),
            "n_test_total": int(total_counts),
            "lr_no_odds": float(lr_no_ll),
            "lr_with_odds": float(lr_with_ll) if lr_with_ll is not None else None,
            "bookmaker": float(book_ll) if book_ll is not None else None,
        })

    print(f"\n{'='*82}")
    print(f"{'WALK-FORWARD VALIDATION — Logistic Regression (B365-valid subset)':^82}")
    print(f"{'='*82}")
    print(f"{'Test Season':<12} {'N Train':<9} {'N Test':<7} {'Total':<7} {'LR (no)':<10} {'LR (odds)':<10} {'Bookmaker':<10}")
    print("-" * 65)
    for r in rows:
        b_str = f"{r['bookmaker']:.4f}" if r['bookmaker'] is not None else "N/A"
        w_str = f"{r['lr_with_odds']:.4f}" if r['lr_with_odds'] is not None else "N/A"
        print(f"{r['test_season']:<12} {r['n_train']:<9} {r['n_test']:<7} {r['n_test_total']:<7} {r['lr_no_odds']:<10.4f} {w_str:<10} {b_str:<10}")

    print("-" * 65)
    avg_no = np.mean([r['lr_no_odds'] for r in rows])
    avg_with = np.mean([r['lr_with_odds'] for r in rows if r['lr_with_odds'] is not None])
    avg_book = np.mean([r['bookmaker'] for r in rows if r['bookmaker'] is not None])
    print(f"{'Average':<12} {'':<9} {'':<7} {'':<7} {avg_no:<10.4f} {avg_with:<10.4f} {avg_book:<10.4f}")

    no_odds = [r['lr_no_odds'] for r in rows]
    with_odds = [r['lr_with_odds'] for r in rows if r['lr_with_odds'] is not None]
    books = [r['bookmaker'] for r in rows if r['bookmaker'] is not None]
    print(f"{'Std Dev':>19} {np.std(no_odds):<10.4f} {np.std(with_odds):<10.4f} {np.std(books):<10.4f}")
    print(f"{'Min':>19} {np.min(no_odds):<10.4f} {np.min(with_odds):<10.4f} {np.min(books):<10.4f}")
    print(f"{'Max':>19} {np.max(no_odds):<10.4f} {np.max(with_odds):<10.4f} {np.max(books):<10.4f}")

    summary = {
        "folds": rows,
        "average": {
            "lr_no_odds": float(avg_no),
            "lr_with_odds": float(avg_with) if avg_with else None,
            "bookmaker": float(avg_book) if avg_book else None,
        },
        "std": {
            "lr_no_odds": float(np.std(no_odds)),
            "lr_with_odds": float(np.std(with_odds)),
            "bookmaker": float(np.std(books)),
        },
    }
    with open(OUTPUT_DIR / "walk_forward_results.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nResults saved to {OUTPUT_DIR / 'walk_forward_results.json'}")


if __name__ == "__main__":
    main()
