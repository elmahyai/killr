import statistics
import time

import numpy as np

from survival.qsurvreg import qsurvreg


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
    p = np.concatenate([np.linspace(0.05, 0.95, 10), [0.5, np.nan]])
    a = qsurvreg(p, 2, 5, distribution="lognormal")
    b = qsurvreg([0.1, 0.25, 0.5, 0.75], 2, 3, distribution="weibull")
    c = qsurvreg(np.linspace(0.1, 0.9, 5), 0, 1, distribution="extreme")
    d = qsurvreg([0.2, 0.5, 0.8], 1, 2, distribution="loglogistic")
    e = qsurvreg(0.5, 2, 5, distribution="gaussian")
    f = qsurvreg([0.1, 0.5, 0.9], 0, 2, distribution="t", parms=4)
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
