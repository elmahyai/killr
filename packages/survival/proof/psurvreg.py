import statistics
import time

import numpy as np

from survival.psurvreg import psurvreg


def fmt(x):
    flat = np.asarray(x, dtype=float).reshape(-1)
    parts = []
    for v in flat:
        if np.isnan(v):
            parts.append("NA")
        else:
            parts.append(f"{v:.17g}")
    return ",".join(parts)


def one():
    q = np.concatenate([np.arange(1, 11, dtype=float), [0.5, np.nan]])
    a = psurvreg(q, 2, 5, distribution="lognormal")
    b = psurvreg([0.5, 1, 2, 3], 2, 3, distribution="weibull")
    c = psurvreg(np.arange(1, 6, dtype=float), 0, 1, distribution="extreme")
    d = psurvreg([1, 2, 3], 1, 2, distribution="loglogistic")
    e = psurvreg(2.5, 2, 5, distribution="gaussian")
    f = psurvreg([0.2, 1, 4], 0, 2, distribution="t", parms=4)
    return [fmt(a), fmt(b), fmt(c), fmt(d), fmt(e), fmt(f)]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
