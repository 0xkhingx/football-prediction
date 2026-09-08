"""Step-2 gated ML batch experiment.

Walk-forward over test seasons [2021..2526]: baseline 23 fair-play cols vs
each candidate set (+ joint batch + B365 positive control), fixed tuned XGB.
SHIP rule: consistent gain sign across folds AND paired-bootstrap 95% CI on
pooled out-of-sample deltas excludes zero. Control must SHIP or the harness
(not the features) is broken.

Writes experiments/results_batch.json. Run: python -m src.experiment_batch
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.impute import SimpleImputer

from .config import (
    EXPERIMENT_SETS,
    FEATURE_COLS_NO_ODDS,
    FEATURIZED_FILE,
    TARGET_MAP,
    TUNED_PARAMS_FILE,
)

RESULTS_FILE = Path("experiments/results_batch.json")
RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)

FOLDS = [2021, 2122, 2223, 2324, 2425, 2526]
N_BOOT = 1000
SEED = 42


def log_loss(y_true, proba, eps=1e-15):
    proba = np.clip(proba, eps, 1 - eps)
    return float(-np.mean([np.log(proba[i, y_true[i]]) for i in range(len(y_true))]))


def load_params():
    with open(TUNED_PARAMS_FILE) as f:
        return json.load(f)


def fit_predict(X_fit, y_fit, X_val, y_val, X_test, params):
    imp = SimpleImputer(strategy="median")
    Xf, Xv, Xt = imp.fit_transform(X_fit), imp.transform(X_val), imp.transform(X_test)
    model = xgb.XGBClassifier(
        objective="multi:softprob", num_class=3, eval_metric="mlogloss",
        random_state=42, early_stopping_rounds=50, verbosity=0, **params,
    )
    model.fit(Xf, y_fit, eval_set=[(Xv, y_val)], verbose=False)
    return model.predict_proba(Xt)


def main():
    df = pd.read_csv(FEATURIZED_FILE, low_memory=False)
    df["target"] = df["FTR"].map(TARGET_MAP)
    params = load_params()

    sets: dict[str, list[str]] = {"baseline": list(FEATURE_COLS_NO_ODDS)}
    for name, cols in EXPERIMENT_SETS.items():
        sets[name] = list(FEATURE_COLS_NO_ODDS) + cols
    sets["joint"] = list(FEATURE_COLS_NO_ODDS) + [c for cols in EXPERIMENT_SETS.values() for c in cols]
    sets["control_odds"] = list(FEATURE_COLS_NO_ODDS) + ["ProbB365H", "ProbB365D", "ProbB365A"]

    per_fold: dict[str, dict] = {name: {} for name in sets}
    pooled: dict[str, list] = {name: [] for name in sets}
    pooled_mask: dict[str, list] = {name: [] for name in sets}
    pooled_y: list = []

    for test_season in FOLDS:
        seasons = sorted(s for s in df["Season"].unique() if s < test_season)
        val_season = seasons[-1]
        fit_seasons = seasons[:-1]
        te = df[df.Season == test_season]
        va = df[df.Season == val_season]
        fi = df[df.Season.isin(fit_seasons)]
        y_te = te["target"].values
        pooled_y.append(y_te)
        print(f"fold test={test_season} fit={len(fi)} val={len(va)} test={len(te)}", flush=True)
        for name, cols in sets.items():
            probs = fit_predict(fi[cols].values, fi["target"].values,
                                va[cols].values, va["target"].values,
                                te[cols].values, params)
            if name == "control_odds":
                # Same-row comparison: mask to odds-complete rows for BOTH
                # models (a few NaN rows must not kill a whole fold).
                mask = ~(np.isnan(te[["ProbB365H", "ProbB365D", "ProbB365A"]].values).any(axis=1))
                if mask.sum() == 0:
                    print(f"  {name:<14} skipped (no odds in fold)", flush=True)
                    per_fold[name][str(test_season)] = None
                    pooled[name].append(None)
                    pooled_mask[name].append(None)
                    continue
                ll = log_loss(y_te[mask], probs[mask])
                print(f"  {name:<14} LL={ll:.4f} (n={mask.sum()})", flush=True)
                per_fold[name][str(test_season)] = ll
                pooled[name].append(probs)
                pooled_mask[name].append(mask)
                continue
            ll = log_loss(y_te, probs)
            per_fold[name][str(test_season)] = ll
            pooled[name].append(probs)
            pooled_mask[name].append(None)
            print(f"  {name:<14} LL={ll:.4f}", flush=True)

    y_all = np.concatenate(pooled_y)
    rng = np.random.default_rng(SEED)
    verdicts = {}
    for name in sets:
        if name == "baseline":
            continue
        # sign consistency over folds where both exist
        signs = []
        for fs in FOLDS:
            b, c = per_fold["baseline"].get(str(fs)), per_fold[name].get(str(fs))
            if b is not None and c is not None:
                signs.append(np.sign(b - c))
        base_probs = [p for p in pooled["baseline"]]
        cand_probs = pooled[name]
        idx = [i for i, p in enumerate(cand_probs) if p is not None]
        if not idx or not signs:
            verdicts[name] = {"verdict": "NO-DATA", "folds": signs}
            continue
        y_pool = np.concatenate([pooled_y[i] for i in idx])
        b_pool = np.concatenate([base_probs[i] for i in idx])
        c_pool = np.concatenate([cand_probs[i] for i in idx if cand_probs[i] is not None])
        masks = [pooled_mask[name][i] for i in idx]
        if any(m is not None for m in masks):
            # Same-row comparison (control): restrict baseline to masked rows too.
            keep_b, keep_c, keep_y = [], [], []
            for i in idx:
                m = pooled_mask[name][i]
                if m is None:
                    keep_b.append(base_probs[i])
                    keep_c.append(cand_probs[i])
                    keep_y.append(pooled_y[i])
                else:
                    keep_b.append(base_probs[i][m])
                    keep_c.append(cand_probs[i][m])
                    keep_y.append(pooled_y[i][m])
            b_pool = np.concatenate(keep_b)
            c_pool = np.concatenate(keep_c)
            y_pool = np.concatenate(keep_y)
        # NOTE sign convention: delta = log c - log b, POSITIVE = candidate
        # better (log-loss is NEGATIVE mean log-prob; LL_b - LL_c = mean delta).
        deltas = np.array([np.log(max(c_pool[i, y_pool[i]], 1e-15)) - np.log(max(b_pool[i, y_pool[i]], 1e-15))
                           for i in range(len(y_pool))])
        boots = np.array([deltas[rng.integers(0, len(deltas), len(deltas))].mean() for _ in range(N_BOOT)])
        lo, hi = float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975))
        mean_gain = float(deltas.mean())
        consistent = all(s > 0 for s in signs)
        ship = consistent and lo > 0
        verdicts[name] = {
            "verdict": "SHIP" if ship else "REJECT",
            "mean_gain": mean_gain,
            "ci95": [lo, hi],
            "folds_positive": f"{sum(1 for s in signs if s > 0)}/{len(signs)}",
            "fold_ll": per_fold[name],
        }
        print(f"{name:<14} gain={mean_gain:+.5f} CI=[{lo:+.5f},{hi:+.5f}] folds+={verdicts[name]['folds_positive']} -> {verdicts[name]['verdict']}", flush=True)

    control = verdicts.get("control_odds", {}).get("verdict")
    harness_ok = control == "SHIP"
    print(f"\npositive control: {control} — harness {'OK' if harness_ok else 'BROKEN'}")

    out = {
        "folds": FOLDS,
        "baseline_fold_ll": per_fold["baseline"],
        "verdicts": verdicts,
        "harness_ok": harness_ok,
        "rule": "SHIP iff gain sign positive in ALL folds AND pooled paired-bootstrap 95% CI excludes zero",
    }
    with open(RESULTS_FILE, "w") as f:
        json.dump(out, f, indent=2)
    print(f"saved {RESULTS_FILE}")


if __name__ == "__main__":
    main()
