"""SHAP analysis for prod XGB-tuned (23 fair-play features)."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import shap

from .config import FEATURE_COLS_NO_ODDS, SPLITS_FILE

OUTPUT_DIR = Path("notebooks")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def main() -> None:
    from .inference import load_artifacts

    data = np.load(SPLITS_FILE)
    X_test = data["X_test"]

    imputer, xgb_model, model_file = load_artifacts()
    print(f"Explaining {model_file}")
    X_test_imp = imputer.transform(X_test)

    sample = X_test_imp[:500]
    explainer = shap.TreeExplainer(xgb_model)
    shap_values = explainer.shap_values(sample)

    shap.summary_plot(
        shap_values,
        sample,
        feature_names=FEATURE_COLS_NO_ODDS,
        show=False,
        class_names=["Home Win", "Draw", "Away Win"],
    )
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "shap_summary.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"SHAP summary plot saved to {OUTPUT_DIR / 'shap_summary.png'}")

    for idx, outcome in enumerate(["Home Win", "Draw", "Away Win"]):
        shap.summary_plot(
            shap_values[:, :, idx],
            sample,
            feature_names=FEATURE_COLS_NO_ODDS,
            show=False,
            plot_type="bar",
            title=f"Feature Importance - {outcome}",
        )
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / f"shap_importance_{outcome.lower().replace(' ', '_')}.png", dpi=150, bbox_inches="tight")
        plt.close()
        print(f"  {outcome} importance saved.")


if __name__ == "__main__":
    main()
