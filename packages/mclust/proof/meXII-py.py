import math
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.me_models import meXII

n, p = 60, 3
x = np.zeros((n, p))
for a in range(1, n + 1):
    for b in range(1, p + 1):
        x[a - 1, b - 1] = math.sin(0.37 * a + 1.3 * b) + 0.4 * math.cos(0.11 * a * b) + 0.05 * a / n * b


def flat(a):
    return np.asarray(a, dtype=float).ravel(order="F").tolist()


def one():
    out = meXII(x)
    v = out["parameters"]["variance"]
    values = [out["returnCode"], out["loglik"]]
    values += flat(out["parameters"]["mean"])
    values += flat(v["sigmasq"])
    return [float(item) for item in values]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for item in value:
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
