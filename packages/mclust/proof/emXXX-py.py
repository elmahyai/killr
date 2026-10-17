import math
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.em_xxx import emXXX

# Fixed inputs. Case A is 6 x 4, B is 60 x 3 (as in meXXX-py.py).
case_a = np.array([[-1.2, .5, 2.1, 1.7], [-.3, .9, 3.2, 1.1], [.4, -.8, 1.3, 2.6],
                   [2.2, 1.5, -1.1, .7], [1.1, -1.7, .2, 3.4], [3.3, .2, 2.4, -.5]])


def make_b():
    n, p = 60, 3
    x = np.zeros((n, p))
    for a in range(1, n + 1):
        for b in range(1, p + 1):
            x[a - 1, b - 1] = math.sin(0.37 * a + 1.3 * b) + 0.4 * math.cos(0.11 * a * b) + 0.05 * a / n * b
    return x


case_b = make_b()


def num(a):
    if a is None:
        return []
    return [float(v) for v in np.asarray(a, dtype=float).ravel(order="F")]


def flat_out(out):
    v = out["parameters"]["variance"]
    vals = []
    vals += num(out.get("returnCode"))
    vals += num(out.get("loglik"))
    vals += num(out["parameters"].get("mean"))
    vals += num(v.get("Sigma"))
    vals += num(v.get("cholSigma"))
    return vals


def one():
    a = emXXX(case_a)
    b = emXXX(case_b)
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
