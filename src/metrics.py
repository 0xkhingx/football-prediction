"""Shared classification metrics. Single implementation — do not reimplement
log-loss/Brier inline elsewhere (past drift source)."""
from __future__ import annotations

import numpy as np


def log_loss(y_true, y_pred_proba, eps: float = 1e-15) -> float:
    y_pred_proba = np.clip(np.asarray(y_pred_proba, dtype=float), eps, 1 - eps)
    y_true = np.asarray(y_true)
    return float(-np.mean([np.log(y_pred_proba[i, y_true[i]]) for i in range(len(y_true))]))


def brier_score(y_true, y_pred_proba) -> float:
    y_pred_proba = np.asarray(y_pred_proba, dtype=float)
    y_true = np.asarray(y_true)
    y_onehot = np.zeros_like(y_pred_proba)
    y_onehot[np.arange(len(y_true)), y_true] = 1
    return float(np.mean(np.sum((y_pred_proba - y_onehot) ** 2, axis=1)))
