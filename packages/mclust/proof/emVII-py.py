import math
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.em_vei_vev_vii_vvi_evv import emVII

# Fixed inputs: x is 60 x 3, as in emVVE-py.py.
n, p = 60, 3
x = np.zeros((n, p))
for a in range(1, n + 1):
    for b in range(1, p + 1):
        x[a - 1, b - 1] = math.sin(0.37 * a + 1.3 * b) + 0.4 * math.cos(0.11 * a * b) + 0.05 * a / n * b

MU = np.array([[0.1, 0.5], [-0.2, 0.4], [0.3, -0.1]])


def num(a):
    if a is None:
        return []
    return [float(v) for v in np.asarray(a, dtype=float).ravel(order="F")]


def flat_out(out):
    v = out["parameters"]["variance"]
    info = out.get("info")
    vals = []
    vals += num(out.get("returnCode"))
    vals += num(out.get("loglik"))
    vals += num(out["parameters"].get("pro"))
    vals += num(out["parameters"].get("mean"))
    vals += num(v.get("scale"))
    vals += num(v.get("shape"))
    vals += num(v.get("sigmasq"))
    vals += num(v.get("orientation"))
    vals += num(v.get("sigma"))
    vals += num(out.get("z"))
    if info is not None:
        vals += [float(info["iterations"]), float(info["error"])]
        inner = info.get("inner")
        if inner is not None:
            vals += [float(inner["iterations"]), float(inner["error"])]
    return vals


def one():
    a = emVII(x, {"pro": np.array([0.4, 0.6]), "mean": MU,
                  "variance": {"sigmasq": np.array([1.3, 0.7])}})
    b = emVII(x, {"pro": np.array([0.3, 0.45, 0.25]), "mean": MU,
                  "variance": {"sigmasq": np.array([1.3, 0.7])},
                  "Vinv": 0.1})
    return flat_out(a) + flat_out(b)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for item in value:
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
