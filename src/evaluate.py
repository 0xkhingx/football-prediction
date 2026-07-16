import numpy as np
import pandas as pd
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.calibration import calibration_curve
import joblib

FEATURIZED_FILE = Path("data/processed/matches_featurized.csv")
SPLITS_FILE = Path("data/processed/splits.npz")
META_FILE = Path("data/processed/split_meta.json")
MODEL_DIR = Path("models")
OUTPUT_DIR = Path("notebooks")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_MAP = {"H": 0, "D": 1, "A": 2}
LEAGUE_MAP = {"E0": "England", "SP1": "Spain", "I1": "Italy", "D1": "Germany", "F1": "France"}

def log_loss(y_true, y_pred_proba, eps=1e-15):
    y_pred_proba = np.clip(y_pred_proba, eps, 1 - eps)
    n = len(y_true)
    loss = 0.0
    for i in range(n):
        loss -= np.log(y_pred_proba[i, y_true[i]])
    return loss / n

def brier_score(y_true, y_pred_proba):
    y_onehot = np.zeros_like(y_pred_proba)
    y_onehot[np.arange(len(y_true)), y_true] = 1
    return np.mean(np.sum((y_pred_proba - y_onehot) ** 2, axis=1))

def main():
    df = pd.read_csv(FEATURIZED_FILE, low_memory=False)
    df["Date"] = pd.to_datetime(df["Date"])
    df["target"] = df["FTR"].map(TARGET_MAP)

    with open(META_FILE) as f:
        meta = json.load(f)

    data = np.load(SPLITS_FILE)
    X_test = data["X_test"]
    y_test = data["y_test"]

    test_season = int(meta["test_season"])
    df_test = df[df["Season"] == test_season].copy()
    df_test = df_test.reset_index(drop=True)

    y_from_df = df_test["target"].values.astype(np.int8)
    aligned = np.all(y_from_df == y_test)
    print(f"Alignment check: df_test FTR matches npz y_test = {aligned}")
    if not aligned:
        mismatches = np.sum(y_from_df != y_test)
        print(f"  WARNING: {mismatches} mismatches! Rebuilding splits...")
        return

    imputer = joblib.load(MODEL_DIR / "imputer.joblib")
    scaler = joblib.load(MODEL_DIR / "scaler.joblib")
    lr = joblib.load(MODEL_DIR / "logistic_regression.joblib")
    xgb_model = joblib.load(MODEL_DIR / "xgboost.joblib")

    X_test_imp = imputer.transform(X_test)
    X_test_scaled = scaler.transform(X_test_imp)

    lr_probs = lr.predict_proba(X_test_scaled)
    xgb_probs = xgb_model.predict_proba(X_test_imp)

    has_odds = df_test["B365H"].notna() & df_test["B365D"].notna() & df_test["B365A"].notna()
    odds_count = int(has_odds.sum())
    print(f"\nTest set: {len(y_test)} total matches, {odds_count} with B365 odds")

    print("\n" + "=" * 60)
    print("FULL TEST SET — all models on same 1752 matches")
    print("=" * 60)
    print(f"{'Model':<28} {'Log-Loss':<12} {'Brier':<12}")
    print("-" * 52)

    naive_prior = np.array([
        np.mean(y_test == 0),
        np.mean(y_test == 1),
        np.mean(y_test == 2),
    ])
    naive_probs = np.tile(naive_prior, (len(y_test), 1))
    naive_ll = log_loss(y_test, naive_probs)
    naive_brier = brier_score(y_test, naive_probs)

    lr_ll = log_loss(y_test, lr_probs)
    lr_brier = brier_score(y_test, lr_probs)
    xgb_ll = log_loss(y_test, xgb_probs)
    xgb_brier = brier_score(y_test, xgb_probs)

    print(f"{'Naive (training prior)':<28} {naive_ll:<12.4f} {naive_brier:<12.4f}")
    print(f"{'Logistic Regression':<28} {lr_ll:<12.4f} {lr_brier:<12.4f}")
    print(f"{'XGBoost':<28} {xgb_ll:<12.4f} {xgb_brier:<12.4f}")

    if odds_count == len(y_test):
        book_raw = np.column_stack([
            1 / df_test["B365H"].values,
            1 / df_test["B365D"].values,
            1 / df_test["B365A"].values,
        ])
        book_sums = book_raw.sum(axis=1, keepdims=True)
        book_probs = book_raw / book_sums
        book_ll = log_loss(y_test, book_probs)
        book_brier = brier_score(y_test, book_probs)
        print(f"{'Bookmaker (B365, normalized)':<28} {book_ll:<12.4f} {book_brier:<12.4f}")

    print("\n" + "=" * 60)
    print("SAME-SUBSET COMPARISON — models vs bookmaker")
    print("(All metrics computed only on the same matches that have B365 odds)")
    print("=" * 60)
    print(f"{'Model':<28} {'Log-Loss':<12} {'Brier':<12}")
    print("-" * 52)

    if odds_count > 0:
        idx = has_odds.values
        y_sub = y_test[idx]
        lr_sub_probs = lr_probs[idx]
        xgb_sub_probs = xgb_probs[idx]
        naive_sub_probs = naive_probs[idx]
        book_raw = np.column_stack([
            1 / df_test.loc[has_odds, "B365H"].values,
            1 / df_test.loc[has_odds, "B365D"].values,
            1 / df_test.loc[has_odds, "B365A"].values,
        ])
        book_sums = book_raw.sum(axis=1, keepdims=True)
        book_probs = book_raw / book_sums

        print(f"{'Naive (training prior)':<28} {log_loss(y_sub, naive_sub_probs):<12.4f} {brier_score(y_sub, naive_sub_probs):<12.4f}")
        print(f"{'Logistic Regression':<28} {log_loss(y_sub, lr_sub_probs):<12.4f} {brier_score(y_sub, lr_sub_probs):<12.4f}")
        print(f"{'XGBoost':<28} {log_loss(y_sub, xgb_sub_probs):<12.4f} {brier_score(y_sub, xgb_sub_probs):<12.4f}")
        print(f"{'Bookmaker (B365, normalized)':<28} {log_loss(y_sub, book_probs):<12.4f} {brier_score(y_sub, book_probs):<12.4f}")
        print(f"\n  N = {odds_count} matches with odds out of {len(y_test)} test matches")

    print("\n" + "=" * 60)
    print("PER-LEAGUE BREAKDOWN (XGBoost)")
    print("=" * 60)
    rows = []
    for code, name in LEAGUE_MAP.items():
        mask = df_test["League"] == code
        if mask.sum() == 0:
            continue
        idx = mask.values
        y_league = y_test[idx]
        xgb_league_probs = xgb_probs[idx]
        ll = log_loss(y_league, xgb_league_probs)
        brier = brier_score(y_league, xgb_league_probs)
        acc = np.mean(xgb_league_probs.argmax(axis=1) == y_league)
        rows.append({"League": f"{name} ({code})", "Matches": int(len(y_league)),
                      "Log-Loss": float(ll), "Brier": float(brier), "Acc": float(acc)})
        print(f"  {name} ({code}): {len(y_league):>4} matches, LL={ll:.4f}, Brier={brier:.4f}, Acc={acc:.3f}")

    print("\n" + "=" * 60)
    print("CALIBRATION ANALYSIS")
    print("=" * 60)
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for idx, outcome in enumerate(["Home Win", "Draw", "Away Win"]):
        prob_true, prob_pred = calibration_curve(
            y_test == idx, xgb_probs[:, idx], n_bins=10
        )
        axes[idx].plot(prob_pred, prob_true, marker="o", label="XGBoost")
        axes[idx].plot([0, 1], [0, 1], "k--", label="Perfect")
        axes[idx].set_xlabel("Predicted Probability")
        axes[idx].set_ylabel("Observed Frequency")
        axes[idx].set_title(outcome)
        axes[idx].legend()
        axes[idx].set_xlim(0, 1)
        axes[idx].set_ylim(0, 1)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "calibration_plot.png", dpi=150)
    print(f"  Calibration plot saved to {OUTPUT_DIR / 'calibration_plot.png'}")

    results = {
        "alignment_check": bool(aligned),
        "test_set_size": len(y_test),
        "odds_subset_size": odds_count,
        "full_test_set": {
            "naive": {"log_loss": float(naive_ll), "brier": float(naive_brier)},
            "logistic_regression": {"log_loss": float(lr_ll), "brier": float(lr_brier)},
            "xgboost": {"log_loss": float(xgb_ll), "brier": float(xgb_brier)},
        },
        "same_subset": {
            "naive": {"log_loss": float(log_loss(y_sub, naive_sub_probs)) if odds_count > 0 else None,
                       "brier": float(brier_score(y_sub, naive_sub_probs)) if odds_count > 0 else None},
            "logistic_regression": {"log_loss": float(log_loss(y_sub, lr_sub_probs)) if odds_count > 0 else None,
                                    "brier": float(brier_score(y_sub, lr_sub_probs)) if odds_count > 0 else None},
            "xgboost": {"log_loss": float(log_loss(y_sub, xgb_sub_probs)) if odds_count > 0 else None,
                         "brier": float(brier_score(y_sub, xgb_sub_probs)) if odds_count > 0 else None},
            "bookmaker": {"log_loss": float(log_loss(y_sub, book_probs)) if odds_count > 0 else None,
                          "brier": float(brier_score(y_sub, book_probs)) if odds_count > 0 else None},
        } if odds_count > 0 else None,
        "per_league": rows,
    }
    with open(MODEL_DIR / "evaluation.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved to {MODEL_DIR / 'evaluation.json'}")

if __name__ == "__main__":
    main()
