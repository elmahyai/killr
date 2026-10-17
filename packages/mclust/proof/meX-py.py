import math
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.me_models import meX

n = 60
x = np.array([math.sin(0.37 * a) + 0.3 * math.cos(1.7 * a) + 0.02 * a for a in range(1, n + 1)])


def flat(a):
    return np.asarray(a, dtype=float).ravel(order="F").tolist()


def one():
    out = meX(x)
    v = out["parameters"]["variance"]
    values = [out["returnCode"], out["loglik"]]
    values += flat(out["parameters"]["mean"])
    values += flat(v["sigmasq"])
    values += flat(out["parameters"]["pro"])
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
