"""Train prod XGB-tuned on 23 fair-play cols. Reproducible entrypoint.

Reads data/processed/splits.npz + models/xgb_best_params.json, refits the
median imputer on current train splits (never reuses a stale one), writes
models/no_odds_imputer.joblib, models/no_odds_xgb_tuned.joblib (+ .ubj)
and models/model_registry.json.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import xgboost as xgb
from sklearn.impute import SimpleImputer

from .config import (
    FEATURE_COLS_NO_ODDS,
    META_FILE,
    MODEL_DIR,
    PROD_IMPUTER_NAME,
    PROD_MODEL_NAME,
    REGISTRY_FILE,
    SPLITS_FILE,
    TUNED_PARAMS_FILE,
)


def log_loss(y_true, proba, eps=1e-15):
    proba = np.clip(proba, eps, 1 - eps)
    return float(-np.mean([np.log(proba[i, y_true[i]]) for i in range(len(y_true))]))


def main() -> None:
    data = np.load(SPLITS_FILE)
    X_train, y_train = data["X_train"], data["y_train"]
    X_val, y_val = data["X_val"], data["y_val"]
    X_test, y_test = data["X_test"], data["y_test"]
    assert X_train.shape[1] == len(FEATURE_COLS_NO_ODDS) == 23, X_train.shape

    with open(TUNED_PARAMS_FILE) as f:
        params = json.load(f)
    with open(META_FILE) as f:
        meta = json.load(f)

    imputer = SimpleImputer(strategy="median")
    Xtr = imputer.fit_transform(X_train)
    Xva = imputer.transform(X_val)
    Xte = imputer.transform(X_test)
    joblib.dump(imputer, MODEL_DIR / f"{PROD_IMPUTER_NAME}.joblib")

    model = xgb.XGBClassifier(
        objective="multi:softprob",
        num_class=3,
        eval_metric="mlogloss",
        random_state=42,
        early_stopping_rounds=50,
        verbosity=0,
        **params,
    )
    model.fit(Xtr, y_train, eval_set=[(Xva, y_val)], verbose=False)

    val_ll = log_loss(y_val, model.predict_proba(Xva))
    test_ll = log_loss(y_test, model.predict_proba(Xte))
    test_acc = float((model.predict_proba(Xte).argmax(1) == y_test).mean())
    print(f"val LL={val_ll:.4f} test LL={test_ll:.4f} acc={test_acc:.3f} best_iter={model.best_iteration}")

    joblib.dump(model, MODEL_DIR / f"{PROD_MODEL_NAME}.joblib")
    model.save_model(str(MODEL_DIR / f"{PROD_MODEL_NAME}.ubj"))

    registry = {
        "model_name": PROD_MODEL_NAME,
        "imputer_name": PROD_IMPUTER_NAME,
        "model_file": f"{PROD_MODEL_NAME}.joblib",
        "framework": f"xgboost {xgb.__version__}",
        "trained_on": str(date.today()),
        "train_seasons": meta["train_seasons"],
        "val_season": meta["val_season"],
        "test_season": meta["test_season"],
        "features": FEATURE_COLS_NO_ODDS,
        "n_features": len(FEATURE_COLS_NO_ODDS),
        "params": params,
        "best_iteration": int(model.best_iteration),
        "metrics": {"val_log_loss": val_ll, "test_log_loss": test_ll, "test_acc": test_acc},
        "fair_play": True,
        "odds_features": [],
    }
    with open(REGISTRY_FILE, "w") as f:
        json.dump(registry, f, indent=2)
    print(f"saved {MODEL_DIR / (PROD_MODEL_NAME + '.joblib')} + {REGISTRY_FILE}")


if __name__ == "__main__":
    main()
