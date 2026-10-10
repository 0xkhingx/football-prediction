"""Train prod XGB-tuned on 23 fair-play cols + LR ensemble + calibration.

Reads data/processed/splits.npz + models/xgb_best_params.json, refits the
median imputer on current train splits (never reuses a stale one), writes
models/no_odds_imputer.joblib, models/no_odds_xgb_tuned.joblib (+ .ubj),
models/no_odds_lr_prod.joblib, models/no_odds_scaler_prod.joblib,
models/no_odds_blend_calibrators.joblib and models/model_registry.json.

Blend: w*xgb + (1-w)*lr with w tuned on val log-loss (grid 0..1 step 0.05).
Calibration: per-outcome isotonic on blended val probs, applied at serve.
Top-level registry metrics are the served path (blend-calibrated).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import joblib
import numpy as np
import xgboost as xgb
from sklearn.impute import SimpleImputer
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

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
from .metrics import log_loss


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

    xgb_val = model.predict_proba(Xva)
    xgb_test = model.predict_proba(Xte)

    # LR head on the same 23 cols (scaled): calibration-stable partner for blend.
    scaler = StandardScaler()
    Xtrs = scaler.fit_transform(Xtr)
    Xvas = scaler.transform(Xva)
    Xtes = scaler.transform(Xte)
    lr = LogisticRegression(max_iter=5000, random_state=42)
    lr.fit(Xtrs, y_train)
    lr_val = lr.predict_proba(Xvas)
    lr_test = lr.predict_proba(Xtes)
    joblib.dump(lr, MODEL_DIR / "no_odds_lr_prod.joblib")
    joblib.dump(scaler, MODEL_DIR / "no_odds_scaler_prod.joblib")

    # Ensemble weight tuned on val only (never test).
    best_w, best_ll = 1.0, log_loss(y_val, xgb_val)
    for w in [i / 20 for i in range(21)]:
        ll = log_loss(y_val, w * xgb_val + (1 - w) * lr_val)
        if ll < best_ll:
            best_ll, best_w = ll, w
    blend_val = best_w * xgb_val + (1 - best_w) * lr_val
    blend_test = best_w * xgb_test + (1 - best_w) * lr_test

    # Per-outcome isotonic on blended val probs (global first; per-league later
    # when 2627 has volume — ~350/fold/league is too thin for 15 calibrators).
    calibrators: dict = {}
    cal_val = np.zeros_like(blend_val)
    cal_test = np.zeros_like(blend_test)
    for k in range(3):
        iso = IsotonicRegression(out_of_bounds="clip")
        iso.fit(blend_val[:, k], (y_val == k).astype(float))
        calibrators[k] = iso
        cal_val[:, k] = iso.transform(blend_val[:, k])
        cal_test[:, k] = iso.transform(blend_test[:, k])
    cal_val = np.clip(cal_val, 1e-15, 1 - 1e-15)
    cal_val /= cal_val.sum(axis=1, keepdims=True)
    cal_test = np.clip(cal_test, 1e-15, 1 - 1e-15)
    cal_test /= cal_test.sum(axis=1, keepdims=True)
    joblib.dump(calibrators, MODEL_DIR / "no_odds_blend_calibrators.joblib")

    val_ll = log_loss(y_val, cal_val)
    test_ll = log_loss(y_test, cal_test)
    test_acc = float(cal_test.argmax(1).__eq__(y_test).mean())
    print(f"val LL={val_ll:.4f} test LL={test_ll:.4f} acc={test_acc:.3f} best_iter={model.best_iteration}")
    print(f"xgb-only val={log_loss(y_val, xgb_val):.4f} test={log_loss(y_test, xgb_test):.4f} | "
          f"lr-only val={log_loss(y_val, lr_val):.4f} test={log_loss(y_test, lr_test):.4f} | "
          f"blend w={best_w:.2f} val={log_loss(y_val, blend_val):.4f} test={log_loss(y_test, blend_test):.4f}")

    joblib.dump(model, MODEL_DIR / f"{PROD_MODEL_NAME}.joblib")
    model.save_model(str(MODEL_DIR / f"{PROD_MODEL_NAME}.ubj"))

    registry = {
        "model_name": PROD_MODEL_NAME,
        "imputer_name": PROD_IMPUTER_NAME,
        "model_file": f"{PROD_MODEL_NAME}.joblib",
        "framework": f"xgboost {xgb.__version__}",
        "trained_on": str(datetime.now(timezone.utc).date()),
        "train_seasons": meta["train_seasons"],
        "val_season": meta["val_season"],
        "test_season": meta["test_season"],
        "features": FEATURE_COLS_NO_ODDS,
        "n_features": len(FEATURE_COLS_NO_ODDS),
        "params": params,
        "best_iteration": int(model.best_iteration),
        "metrics": {"val_log_loss": val_ll, "test_log_loss": test_ll, "test_acc": test_acc},
        "components": {
            "xgb": {"val_log_loss": log_loss(y_val, xgb_val), "test_log_loss": log_loss(y_test, xgb_test)},
            "lr": {"val_log_loss": log_loss(y_val, lr_val), "test_log_loss": log_loss(y_test, lr_test)},
            "blend_uncalibrated": {"val_log_loss": log_loss(y_val, blend_val),
                                   "test_log_loss": log_loss(y_test, blend_test)},
        },
        "ensemble": {
            "lr_model": "no_odds_lr_prod",
            "scaler": "no_odds_scaler_prod",
            "calibrators": "no_odds_blend_calibrators",
            "xgb_weight": best_w,
        },
        "fair_play": True,
        "odds_features": [],
    }
    with open(REGISTRY_FILE, "w") as f:
        json.dump(registry, f, indent=2)
    print(f"saved {MODEL_DIR / (PROD_MODEL_NAME + '.joblib')} + {REGISTRY_FILE}")


if __name__ == "__main__":
    main()
