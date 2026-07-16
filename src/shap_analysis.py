import numpy as np
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
import shap
import joblib

SPLITS_FILE = Path("data/processed/splits.npz")
META_FILE = Path("data/processed/split_meta.json")
MODEL_DIR = Path("models")
OUTPUT_DIR = Path("notebooks")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FEATURE_NAMES = [
    "EloHome", "EloAway", "EloDiff",
    "HomeForm5", "HomeForm10", "AwayForm5", "AwayForm10",
    "H2HStreak", "HomeRest", "AwayRest",
    "HomeGoalsAvg5", "AwayGoalsAvg5",
    "HomeGoalsConcededAvg5", "AwayGoalsConcededAvg5",
]

def main():
    data = np.load(SPLITS_FILE)
    X_train = data["X_train"]
    X_test = data["X_test"]
    y_test = data["y_test"]

    imputer = joblib.load(MODEL_DIR / "imputer.joblib")
    X_train_imp = imputer.transform(X_train)
    X_test_imp = imputer.transform(X_test)

    xgb_model = joblib.load(MODEL_DIR / "xgboost.joblib")

    sample = X_test_imp[:500]
    explainer = shap.TreeExplainer(xgb_model)
    shap_values = explainer.shap_values(sample)

    shap.summary_plot(
        shap_values, sample, feature_names=FEATURE_NAMES,
        show=False, class_names=["Home Win", "Draw", "Away Win"],
    )
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "shap_summary.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"SHAP summary plot saved to {OUTPUT_DIR / 'shap_summary.png'}")

    for idx, outcome in enumerate(["Home Win", "Draw", "Away Win"]):
        shap.summary_plot(
            shap_values[:, :, idx], sample, feature_names=FEATURE_NAMES,
            show=False, plot_type="bar", title=f"Feature Importance - {outcome}",
        )
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / f"shap_importance_{outcome.lower().replace(' ', '_')}.png", dpi=150, bbox_inches="tight")
        plt.close()
        print(f"  {outcome} importance saved.")

    print("Per-outcome feature importance plots saved.")

if __name__ == "__main__":
    main()
