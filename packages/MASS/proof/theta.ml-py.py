import importlib.util
import statistics
import sys
import time
from pathlib import Path

import numpy as np

_pkg = Path(__file__).resolve().parents[1] / "mass"
_spec = importlib.util.spec_from_file_location("mass.theta_ml", _pkg / "theta_ml.py")
_theta_ml_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_theta_ml_mod)
theta_ml = _theta_ml_mod.theta_ml


def one():
    y = np.array([7, 5, 4, 2, 11, 0, 3, 9, 6, 1, 8, 4, 2, 5, 0], dtype=float)
    mu = np.array(
        [
            5.2, 4.8, 4.1, 2.5, 9.0, 0.6, 3.2, 8.1, 5.9, 1.2,
            7.4, 3.9, 2.8, 4.6, 0.4,
        ],
        dtype=float,
    )
    w = np.array([1, 1, 2, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1], dtype=float)
    th = theta_ml(y, mu, weights=w)
    return np.array([float(th), th.SE], dtype=float)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for item in value:
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
