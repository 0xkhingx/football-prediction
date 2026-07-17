import numpy as np
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

def log_loss(y_true, y_pred_proba, eps=1e-15):
    y_pred_proba = np.clip(y_pred_proba, eps, 1 - eps)
    n = len(y_true)
    loss = 0.0
    for i in range(n):
        loss -= np.log(y_pred_proba[i, y_true[i]])
    return loss / n

def train_model(X_train, y_train, X_val, y_val, X_test, y_test, label, prefix):
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
    joblib.dump(lr, MODEL_DIR / f"{prefix}_logistic_regression.joblib")
    joblib.dump(imputer, MODEL_DIR / f"{prefix}_imputer.joblib")
    joblib.dump(scaler, MODEL_DIR / f"{prefix}_scaler.joblib")

    lr_val_ll = log_loss(y_val, lr.predict_proba(X_val_scaled))
    lr_test_ll = log_loss(y_test, lr.predict_proba(X_test_scaled))

    xgb_model = xgb.XGBClassifier(
        objective="multi:softprob", num_class=3, eval_metric="mlogloss",
        n_estimators=500, max_depth=6, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, min_child_weight=3,
        reg_alpha=0.1, reg_lambda=1.0, random_state=42,
        early_stopping_rounds=50, verbosity=0,
    )
    xgb_model.fit(
        X_train_imp, y_train,
        eval_set=[(X_val_imp, y_val)],
        verbose=False,
    )
    joblib.dump(xgb_model, MODEL_DIR / f"{prefix}_xgboost.joblib")

    xgb_val_ll = log_loss(y_val, xgb_model.predict_proba(X_val_imp))
    xgb_test_ll = log_loss(y_test, xgb_model.predict_proba(X_test_imp))

    print(f"\n{label}:")
    print(f"  Train: {X_train.shape}, Val: {X_val.shape}, Test: {X_test.shape}")
    print(f"  {'':>20} {'Val LL':<10} {'Test LL':<10}")
    print(f"  {'Logistic Regression':>20} {lr_val_ll:<10.4f} {lr_test_ll:<10.4f}")
    print(f"  {'XGBoost':>20} {xgb_val_ll:<10.4f} {xgb_test_ll:<10.4f}")

    return {
        "label": label,
        "n_features": X_train.shape[1],
        "logistic_regression": {"val_log_loss": float(lr_val_ll), "test_log_loss": float(lr_test_ll)},
        "xgboost": {"val_log_loss": float(xgb_val_ll), "test_log_loss": float(xgb_test_ll),
                     "best_iteration": int(xgb_model.best_iteration)},
    }

def main():
    data = np.load(SPLITS_FILE)
    with open(META_FILE) as f:
        meta = json.load(f)

    has_odds = "X_train_odds" in data

    results = {}

    res = train_model(
        data["X_train"], data["y_train"],
        data["X_val"], data["y_val"],
        data["X_test"], data["y_test"],
        "Model without odds", "no_odds",
    )
    results["no_odds"] = res

    if has_odds:
        res = train_model(
            data["X_train_odds"], data["y_train"],
            data["X_val_odds"], data["y_val"],
            data["X_test_odds"], data["y_test"],
            "Model with odds", "with_odds",
        )
        results["with_odds"] = res

    naive_prior = np.mean(data["y_train"] == 0)
    naive_draw = np.mean(data["y_train"] == 1)
    naive_away = np.mean(data["y_train"] == 2)
    naive_probs = np.zeros((len(data["y_test"]), 3))
    naive_probs[:, 0] = naive_prior
    naive_probs[:, 1] = naive_draw
    naive_probs[:, 2] = naive_away
    naive_ll = log_loss(data["y_test"], naive_probs)
    results["naive_prior"] = {
        "test_log_loss": float(naive_ll),
        "priors": {"H": float(naive_prior), "D": float(naive_draw), "A": float(naive_away)},
    }

    print(f"\n{'':>25} {'Test Log-Loss':>15}")
    print("-" * 42)
    print(f"{'Naive (prior)':>25} {naive_ll:>15.4f}")
    print(f"{'LR (no odds)':>25} {results['no_odds']['logistic_regression']['test_log_loss']:>15.4f}")
    print(f"{'XGB (no odds)':>25} {results['no_odds']['xgboost']['test_log_loss']:>15.4f}")
    if has_odds:
        print(f"{'LR (with odds)':>25} {results['with_odds']['logistic_regression']['test_log_loss']:>15.4f}")
        print(f"{'XGB (with odds)':>25} {results['with_odds']['xgboost']['test_log_loss']:>15.4f}")

    with open(MODEL_DIR / "results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {MODEL_DIR / 'results.json'}")

if __name__ == "__main__":
    main()
