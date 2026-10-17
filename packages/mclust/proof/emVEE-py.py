import math
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.em_models import emVEE

n, p = 60, 3
x = np.zeros((n, p))
for a in range(1, n + 1):
    for b in range(1, p + 1):
        x[a - 1, b - 1] = math.sin(0.37 * a + 1.3 * b) + 0.4 * math.cos(0.11 * a * b) + 0.05 * a / n * b

MU = np.array([[0.1, 0.5], [-0.2, 0.4], [0.3, -0.1]])
ang_a = math.pi / 6
ang_b = math.pi / 5
Rz = np.array([[math.cos(ang_a), -math.sin(ang_a), 0.0], [math.sin(ang_a), math.cos(ang_a), 0.0], [0.0, 0.0, 1.0]])
Rx = np.array([[1.0, 0.0, 0.0], [0.0, math.cos(ang_b), -math.sin(ang_b)], [0.0, math.sin(ang_b), math.cos(ang_b)]])
O = Rz @ Rx


def pars(pro, scale, shape, Vinv=None):
    out = {
        "pro": np.asarray(pro, dtype=float),
        "mean": MU,
        "variance": {
            "scale": np.asarray(scale, dtype=float),
            "shape": np.asarray(shape, dtype=float),
            "orientation": O,
        },
    }
    if Vinv is not None:
        out["Vinv"] = Vinv
    return out


def flat(a):
    return np.asarray(a, dtype=float).ravel(order="F").tolist()


def case_values(out):
    v = out["parameters"]["variance"]
    values = [out["returnCode"], out["loglik"]]
    values += flat(out["parameters"]["pro"])
    values += flat(out["parameters"]["mean"])
    values += flat(v["scale"])
    values += flat(v["shape"])
    values += flat(v["orientation"])
    values += flat(v["sigma"])
    values += flat(out["z"])
    values += [out["info"]["niterout"], out["info"]["errout"]]
    values += [out["info"]["inner"]["niterin"], out["info"]["inner"]["errin"]]
    return values


def one():
    a = emVEE(x, pars([0.4, 0.6], [1.3, 0.7], [1.5, 0.6, 0.9]))
    b = emVEE(x, pars([0.3, 0.45, 0.25], [1.3, 0.7], [1.5, 0.6, 0.9], Vinv=0.15))
    return [float(item) for item in case_values(a) + case_values(b)]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for item in value:
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
