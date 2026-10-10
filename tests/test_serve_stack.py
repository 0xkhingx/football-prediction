"""Blend + calibration serving: identity fallbacks + math correctness."""
import numpy as np

from src.inference import apply_calibrators, apply_honesty_gate


def test_calibrators_absent_is_identity():
    p = np.array([[0.5, 0.3, 0.2]])
    out = apply_calibrators(p, None)
    assert np.allclose(out, p)


def test_calibrators_renormalize():
    class _Iso:
        def transform(self, x):
            return np.asarray(x) * 2  # deliberately unnormalized

    cal = {0: _Iso(), 1: _Iso(), 2: _Iso()}
    out = apply_calibrators(np.array([[0.5, 0.3, 0.2]]), cal)
    assert abs(out.sum() - 1.0) < 1e-9
    assert (out >= 0).all()


def test_blend_math():
    xgb = np.array([0.6, 0.25, 0.15])
    lr = np.array([0.4, 0.35, 0.25])
    w = 0.7
    blend = w * xgb + (1 - w) * lr
    assert abs(blend.sum() - 1.0) < 1e-9
    assert int(np.argmax(blend)) == 0
    g = apply_honesty_gate(blend)
    assert g["call"] == (float(np.max(blend)) >= g["threshold"])
