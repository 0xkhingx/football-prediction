import numpy as np
import json
import random
from pathlib import Path
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

def main():
    data = np.load(SPLITS_FILE)
    X_train = data["X_train"]
    y_train = data["y_train"]
    X_val = data["X_val"]
    y_val = data["y_val"]
    X_test = data["X_test"]
    y_test = data["y_test"]

    print(f"Train: {X_train.shape}, Val: {X_val.shape}, Test: {X_test.shape}")

    imputer = SimpleImputer(strategy="median")
    X_train_imp = imputer.fit_transform(X_train)
    X_val_imp = imputer.transform(X_val)
    X_test_imp = imputer.transform(X_test)

    untuned = xgb.XGBClassifier(
        objective="multi:softprob", num_class=3, eval_metric="mlogloss",
        n_estimators=500, max_depth=6, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, min_child_weight=3,
        reg_alpha=0.1, reg_lambda=1.0, random_state=42,
        early_stopping_rounds=50, verbosity=0,
    )
    untuned.fit(X_train_imp, y_train, eval_set=[(X_val_imp, y_val)], verbose=False)
    untuned_val_ll = log_loss(y_val, untuned.predict_proba(X_val_imp))
    untuned_test_ll = log_loss(y_test, untuned.predict_proba(X_test_imp))

    param_grid = {
        "max_depth": [3, 4, 5, 6, 7, 8, 9, 10],
        "learning_rate": [0.01, 0.02, 0.03, 0.05, 0.08, 0.1, 0.2, 0.3],
        "subsample": [0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
        "colsample_bytree": [0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
        "min_child_weight": [1, 2, 3, 5, 7, 10],
        "reg_alpha": [0, 0.01, 0.1, 0.5, 1, 5],
        "reg_lambda": [0, 0.1, 0.5, 1, 2, 5],
        "n_estimators": [100, 200, 300, 500, 750, 1000],
    }

    rng = random.Random(42)
    best_val_ll = float("inf")
    best_params = None
    best_model = None
    n_trials = 50

    print(f"\nRunning {n_trials} random parameter combinations...")

    for trial in range(n_trials):
        params = {k: rng.choice(v) for k, v in param_grid.items()}

        model = xgb.XGBClassifier(
            objective="multi:softprob", num_class=3, eval_metric="mlogloss",
            n_estimators=params["n_estimators"],
            max_depth=params["max_depth"],
            learning_rate=params["learning_rate"],
            subsample=params["subsample"],
            colsample_bytree=params["colsample_bytree"],
            min_child_weight=params["min_child_weight"],
            reg_alpha=params["reg_alpha"],
            reg_lambda=params["reg_lambda"],
            random_state=42,
            early_stopping_rounds=50,
            verbosity=0,
        )
        model.fit(
            X_train_imp, y_train,
            eval_set=[(X_val_imp, y_val)],
            verbose=False,
        )

        val_probs = model.predict_proba(X_val_imp)
        val_ll = log_loss(y_val, val_probs)

        if val_ll < best_val_ll:
            best_val_ll = val_ll
            best_params = params
            best_model = model

    best_val_probs = best_model.predict_proba(X_val_imp)
    best_test_probs = best_model.predict_proba(X_test_imp)
    best_val_ll_final = log_loss(y_val, best_val_probs)
    best_test_ll_final = log_loss(y_test, best_test_probs)

    print("\n" + "=" * 70)
    print("XGBOOST HYPERPARAMETER TUNING RESULTS")
    print("=" * 70)
    print(f"\nSearch budget: {n_trials} random parameter combinations (manual loop)")
    print(f"Best validation log-loss found: {best_val_ll_final:.4f}")
    print(f"\nBest parameters:")
    for p, v in best_params.items():
        print(f"  {p}: {v}")
    print(f"\n{'':<20} {'Val Log-Loss':<15} {'Test Log-Loss':<15}")
    print("-" * 50)
    print(f"{'Untuned':<20} {untuned_val_ll:<15.4f} {untuned_test_ll:<15.4f}")
    print(f"{'Tuned':<20} {best_val_ll_final:<15.4f} {best_test_ll_final:<15.4f}")
    print(f"{'Improvement':<20} {untuned_val_ll - best_val_ll_final:<+15.4f} {untuned_test_ll - best_test_ll_final:<+15.4f}")

    with open(MODEL_DIR / "xgb_best_params.json", "w") as f:
        json.dump(best_params, f, indent=2)
    print(f"\nBest params saved to {MODEL_DIR / 'xgb_best_params.json'}")

    best_model.save_model(str(MODEL_DIR / "xgboost_tuned.ubj"))
    joblib.dump(best_model, MODEL_DIR / "xgboost_tuned.joblib")
    print(f"Tuned model saved to {MODEL_DIR / 'xgboost_tuned.joblib'}")

if __name__ == "__main__":
    main()
