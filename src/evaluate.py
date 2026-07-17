import numpy as np
import pandas as pd
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.calibration import calibration_curve
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
import joblib

FEATURIZED_FILE = Path("data/processed/matches_featurized.csv")
SPLITS_FILE = Path("data/processed/splits.npz")
META_FILE = Path("data/processed/split_meta.json")
MODEL_DIR = Path("models")
OUTPUT_DIR = Path("notebooks")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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
    df["target"] = df["FTR"].map({"H": 0, "D": 1, "A": 2})

    with open(META_FILE) as f:
        meta = json.load(f)

    data = np.load(SPLITS_FILE)
    y_test = data["y_test"]

    test_season = int(meta["test_season"])
    df_test = df[df["Season"] == test_season].copy().reset_index(drop=True)

    y_from_df = df_test["target"].values.astype(np.int8)
    aligned = np.all(y_from_df == y_test)
    print(f"Alignment check: df_test FTR matches npz y_test = {aligned}")
    if not aligned:
        mismatches = np.sum(y_from_df != y_test)
        print(f"  WARNING: {mismatches} mismatches — aborting")
        return
    X_test = data["X_test"]

    no_imputer = joblib.load(MODEL_DIR / "no_odds_imputer.joblib")
    no_scaler = joblib.load(MODEL_DIR / "no_odds_scaler.joblib")
    X_test_imp = no_imputer.transform(X_test)
    X_test_scaled = no_scaler.transform(X_test_imp)

    lr_no_odds = joblib.load(MODEL_DIR / "no_odds_logistic_regression.joblib")
    xgb_no_odds = joblib.load(MODEL_DIR / "no_odds_xgboost.joblib")
    lr_no_probs = lr_no_odds.predict_proba(X_test_scaled)
    xgb_no_probs = xgb_no_odds.predict_proba(X_test_imp)

    has_odds = "X_test_odds" in data
    if has_odds:
        X_test_odds = data["X_test_odds"]
        with_imputer = joblib.load(MODEL_DIR / "with_odds_imputer.joblib")
        with_scaler = joblib.load(MODEL_DIR / "with_odds_scaler.joblib")
        X_test_odds_imp = with_imputer.transform(X_test_odds)
        X_test_odds_scaled = with_scaler.transform(X_test_odds_imp)
        lr_with = joblib.load(MODEL_DIR / "with_odds_logistic_regression.joblib")
        xgb_with = joblib.load(MODEL_DIR / "with_odds_xgboost.joblib")
        lr_with_probs = lr_with.predict_proba(X_test_odds_scaled)
        xgb_with_probs = xgb_with.predict_proba(X_test_odds_imp)

    has_odds_in_df = df_test["B365H"].notna() & df_test["B365D"].notna() & df_test["B365A"].notna()
    odds_count = int(has_odds_in_df.sum())
    print(f"\nTest set: {len(y_test)} matches, B365 odds coverage: {odds_count}/{len(y_test)}")

    print("\n" + "=" * 70)
    print("TEST SET RESULTS — all models on the SAME 1752 matches")
    print("=" * 70)
    print(f"{'Model':<30} {'Log-Loss':<12} {'Brier':<12}")
    print("-" * 54)

    naive_prior = np.array([np.mean(y_test == 0), np.mean(y_test == 1), np.mean(y_test == 2)])
    naive_probs = np.tile(naive_prior, (len(y_test), 1))
    naive_ll = log_loss(y_test, naive_probs)
    naive_brier = brier_score(y_test, naive_probs)
    print(f"{'Naive (training prior)':<30} {naive_ll:<12.4f} {naive_brier:<12.4f}")

    print(f"{'LR (no odds)':<30} {log_loss(y_test, lr_no_probs):<12.4f} {brier_score(y_test, lr_no_probs):<12.4f}")
    print(f"{'XGB (no odds)':<30} {log_loss(y_test, xgb_no_probs):<12.4f} {brier_score(y_test, xgb_no_probs):<12.4f}")

    if has_odds:
        print(f"{'LR (with B365 odds)':<30} {log_loss(y_test, lr_with_probs):<12.4f} {brier_score(y_test, lr_with_probs):<12.4f}")
        print(f"{'XGB (with B365 odds)':<30} {log_loss(y_test, xgb_with_probs):<12.4f} {brier_score(y_test, xgb_with_probs):<12.4f}")

    book_raw = np.column_stack([1 / df_test[c].values for c in ["B365H", "B365D", "B365A"]])
    book_probs = book_raw / book_raw.sum(axis=1, keepdims=True)
    book_ll = log_loss(y_test, book_probs)
    book_brier = brier_score(y_test, book_probs)
    print(f"{'Bookmaker (B365, normalized)':<30} {book_ll:<12.4f} {book_brier:<12.4f}")

    print("\n" + "=" * 70)
    print("PER-LEAGUE BREAKDOWN — XGBoost with odds")
    print("=" * 70)
    rows = []
    for code, name in LEAGUE_MAP.items():
        mask = df_test["League"] == code
        if mask.sum() == 0:
            continue
        idx = mask.values
        y_league = y_test[idx]
        probs_league = (xgb_with_probs if has_odds else xgb_no_probs)[idx]
        ll = log_loss(y_league, probs_league)
        brier = brier_score(y_league, probs_league)
        acc = np.mean(probs_league.argmax(axis=1) == y_league)
        rows.append({"League": f"{name} ({code})", "Matches": int(len(y_league)),
                      "Log-Loss": float(ll), "Brier": float(brier), "Acc": float(acc)})
        ll_no = log_loss(y_league, xgb_no_probs[idx])
        print(f"  {name} ({code}): {len(y_league):>4} matches, LL={ll:.4f} (no odds: {ll_no:.4f}), Acc={acc:.3f}")

    print("\n" + "=" * 70)
    print("CALIBRATION ANALYSIS — XGBoost with odds")
    print("=" * 70)
    probs = xgb_with_probs if has_odds else xgb_no_probs
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for idx, outcome in enumerate(["Home Win", "Draw", "Away Win"]):
        prob_true, prob_pred = calibration_curve(y_test == idx, probs[:, idx], n_bins=10)
        axes[idx].plot(prob_pred, prob_true, marker="o", label="XGBoost (with odds)" if has_odds else "XGBoost (no odds)")
        prob_true_b, prob_pred_b = calibration_curve(y_test == idx, book_probs[:, idx], n_bins=10)
        axes[idx].plot(prob_pred_b, prob_true_b, marker="s", label="Bookmaker", alpha=0.7)
        axes[idx].plot([0, 1], [0, 1], "k--", label="Perfect")
        axes[idx].set_xlabel("Predicted Probability")
        axes[idx].set_ylabel("Observed Frequency")
        axes[idx].set_title(outcome)
        axes[idx].legend(fontsize=8)
        axes[idx].set_xlim(0, 1)
        axes[idx].set_ylim(0, 1)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "calibration_plot.png", dpi=150)
    print(f"  Calibration plot saved to {OUTPUT_DIR / 'calibration_plot.png'}")

    results = {
        "alignment_check": bool(aligned),
        "test_set_size": int(len(y_test)),
        "test_season": int(test_season),
        "odds_coverage": f"{odds_count}/{len(y_test)}",
        "naive": {"log_loss": float(naive_ll), "brier": float(naive_brier)},
        "no_odds": {
            "logistic_regression": {"log_loss": float(log_loss(y_test, lr_no_probs)), "brier": float(brier_score(y_test, lr_no_probs))},
            "xgboost": {"log_loss": float(log_loss(y_test, xgb_no_probs)), "brier": float(brier_score(y_test, xgb_no_probs))},
        },
        "bookmaker": {"log_loss": float(book_ll), "brier": float(book_brier)},
        "per_league": rows,
    }
    if has_odds:
        results["with_odds"] = {
            "logistic_regression": {"log_loss": float(log_loss(y_test, lr_with_probs)), "brier": float(brier_score(y_test, lr_with_probs))},
            "xgboost": {"log_loss": float(log_loss(y_test, xgb_with_probs)), "brier": float(brier_score(y_test, xgb_with_probs))},
        }

    with open(MODEL_DIR / "evaluation.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved to {MODEL_DIR / 'evaluation.json'}")

if __name__ == "__main__":
    main()
