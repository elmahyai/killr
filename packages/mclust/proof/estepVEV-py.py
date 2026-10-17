import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.estep_v_vei_vev_vii_vvi_vvv import estepVEV

n = 40
p = 3
G = 3
i = np.arange(1, n + 1, dtype=float)
x = np.column_stack([np.sin(0.7 * i), 0.7 * np.cos(1.3 * i) + 0.1 * i / n, np.sin(0.4 * i + 1) - 0.5 * i / n])
mu = np.array([[-0.5, 0.2, 0.1], [0.4, -0.3, 0.6], [0.0, 0.9, -0.8]])
O = np.zeros((p, p, G))
for g in range(1, G + 1):
    v = np.array([1.0, g, 2.0])
    O[:, :, g - 1] = np.eye(p) - 2 * np.outer(v, v) / np.dot(v, v)
pro3 = np.array([0.3, 0.45, 0.25])
pro4 = np.array([0.2, 0.3, 0.3, 0.2])


def pars(pro):
    return {
        "pro": pro,
        "mean": mu,
        "variance": {
            "scale": np.array([0.6, 1.4, 0.9]),
            "shape": np.array([1.5, 0.7, 1.1]),
            "orientation": O,
        },
    }


def one():
    a = estepVEV(x, pars(pro3))
    b = estepVEV(x, pars(pro4))
    return np.concatenate([a["z"].ravel(order="F"), [a["loglik"]], b["z"].ravel(order="F"), [b["loglik"]]])


value = one()
elapsed = []
for _ in range(20):
    t0 = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - t0) * 1000)
print("\n".join("%.17g" % v for v in value))
print("%.17g" % statistics.median(elapsed))
