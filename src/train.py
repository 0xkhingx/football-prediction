import numpy as np
import pandas as pd
import json
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
import xgboost as xgb
import joblib

SPLITS_FILE = Path("data/processed/splits.npz")
META_FILE = Path("data/processed/split_meta.json")
MODEL_DIR = Path("models")
MODEL_DIR.mkdir(parents=True, exist_ok=True)

TARGET_MAP = {"H": 0, "D": 1, "A": 2}

def log_loss(y_true, y_pred_proba, eps=1e-15):
    y_pred_proba = np.clip(y_pred_proba, eps, 1 - eps)
    n = len(y_true)
    loss = 0
    for i in range(n):
        loss -= np.log(y_pred_proba[i, y_true[i]])
    return loss / n

def main():
    data = np.load(SPLITS_FILE)
    X_train = data["X_train"]
    y_train = data["y_train"]
    X_val = data["X_val"]
    y_val = data["y_val"]
    X_test = data["X_test"]
    y_test = data["y_test"]

    with open(META_FILE) as f:
        meta = json.load(f)

    print(f"Train: {X_train.shape}, Val: {X_val.shape}, Test: {X_test.shape}")

    imputer = SimpleImputer(strategy="median")
    X_train_imp = imputer.fit_transform(X_train)
    X_val_imp = imputer.transform(X_val)
    X_test_imp = imputer.transform(X_test)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_imp)
    X_val_scaled = scaler.transform(X_val_imp)
    X_test_scaled = scaler.transform(X_test_imp)

    lr = LogisticRegression(max_iter=5000, random_state=42)
    lr.fit(X_train_scaled, y_train)
    joblib.dump(lr, MODEL_DIR / "logistic_regression.joblib")
    joblib.dump(scaler, MODEL_DIR / "scaler.joblib")
    joblib.dump(imputer, MODEL_DIR / "imputer.joblib")

    lr_val_pred = lr.predict_proba(X_val_scaled)
    lr_val_ll = log_loss(y_val, lr_val_pred)
    lr_test_pred = lr.predict_proba(X_test_scaled)
    lr_test_ll = log_loss(y_test, lr_test_pred)
    print(f"\nLogistic Regression:")
    print(f"  Val log-loss:  {lr_val_ll:.4f}")
    print(f"  Test log-loss: {lr_test_ll:.4f}")

    xgb_model = xgb.XGBClassifier(
        objective="multi:softprob",
        num_class=3,
        eval_metric="mlogloss",
        n_estimators=500,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
        early_stopping_rounds=50,
        verbosity=1,
    )
    xgb_model.fit(
        X_train_imp, y_train,
        eval_set=[(X_val_imp, y_val)],
        verbose=False,
    )

    joblib.dump(xgb_model, MODEL_DIR / "xgboost.joblib")

    xgb_val_pred = xgb_model.predict_proba(X_val_imp)
    xgb_val_ll = log_loss(y_val, xgb_val_pred)
    xgb_test_pred = xgb_model.predict_proba(X_test_imp)
    xgb_test_ll = log_loss(y_test, xgb_test_pred)
    print(f"XGBoost:")
    print(f"  Best iteration: {xgb_model.best_iteration}")
    print(f"  Val log-loss:  {xgb_val_ll:.4f}")
    print(f"  Test log-loss: {xgb_test_ll:.4f}")

    naive_home_pred = np.zeros((len(y_test), 3))
    home_prior = np.mean(y_train == 0)
    draw_prior = np.mean(y_train == 1)
    away_prior = np.mean(y_train == 2)
    naive_home_pred[:, 0] = home_prior
    naive_home_pred[:, 1] = draw_prior
    naive_home_pred[:, 2] = away_prior
    naive_ll = log_loss(y_test, naive_home_pred)
    print(f"Naive (prior distribution):")
    print(f"  Test log-loss: {naive_ll:.4f}")
    print(f"  Priors [H/D/A]: {home_prior:.3f} / {draw_prior:.3f} / {away_prior:.3f}")

    results = {
        "logistic_regression": {
            "val_log_loss": float(lr_val_ll),
            "test_log_loss": float(lr_test_ll),
        },
        "xgboost": {
            "val_log_loss": float(xgb_val_ll),
            "test_log_loss": float(xgb_test_ll),
            "best_iteration": int(xgb_model.best_iteration),
        },
        "naive_prior": {
            "test_log_loss": float(naive_ll),
            "priors": {"H": float(home_prior), "D": float(draw_prior), "A": float(away_prior)},
        },
    }
    with open(MODEL_DIR / "results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nModels and results saved to {MODEL_DIR}/")

if __name__ == "__main__":
    main()
