import math
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.mvn import mvnXXX

# Fixed inputs. Case A is 6 x 4, B is 60 x 3, C is 25 x 2.
case_a = np.array([[-1.2, .5, 2.1, 1.7], [-.3, .9, 3.2, 1.1], [.4, -.8, 1.3, 2.6],
                   [2.2, 1.5, -1.1, .7], [1.1, -1.7, .2, 3.4], [3.3, .2, 2.4, -.5]])


def make_b():
    n, p = 60, 3
    x = np.zeros((n, p))
    for a in range(1, n + 1):
        for b in range(1, p + 1):
            x[a - 1, b - 1] = math.sin(0.37 * a + 1.3 * b) + 0.4 * math.cos(0.11 * a * b) + 0.05 * a / n * b
    return x


def make_c():
    n, p = 25, 2
    x = np.zeros((n, p))
    for a in range(1, n + 1):
        for b in range(1, p + 1):
            x[a - 1, b - 1] = math.cos(0.7 * a + b) + 0.2 * math.sin(1.9 * a * b) + 0.01 * a * b
    return x


cases = [case_a, make_b(), make_c()]


def flat(a):
    return np.asarray(a, dtype=float).ravel(order="F").tolist()


def one(x):
    out = mvnXXX(x)
    v = out["parameters"]["variance"]
    values = [out["returnCode"], out["loglik"]]
    values += flat(out["parameters"]["mean"])
    values += flat(v["Sigma"])
    values += flat(v["cholSigma"])
    return [float(item) for item in values]


vals = []
for x in cases:
    vals += one(x)
primary = cases[1]
one(primary)
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one(primary)
    elapsed.append((time.perf_counter() - started) * 1000)
for item in vals:
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
