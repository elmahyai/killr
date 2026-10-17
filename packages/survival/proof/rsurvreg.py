import statistics
import time

import numpy as np

from survival.rsurvreg import rsurvreg, set_seed


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
    set_seed(42)
    a = rsurvreg(8, 2, 5, distribution="lognormal")
    set_seed(7)
    b = rsurvreg(6, 1, 2, distribution="weibull")
    set_seed(123)
    d = rsurvreg(5, [0, 1, 2, 3, 4], 1, distribution="extreme")
    set_seed(2024)
    e = rsurvreg(6, 1, 2, distribution="loglogistic")
    set_seed(99)
    f = rsurvreg(4, 2, 5, distribution="gaussian")
    set_seed(5)
    g = rsurvreg(5, 0, 2, distribution="t", parms=4)
    return [fmt(a), fmt(b), fmt(d), fmt(e), fmt(f), fmt(g)]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
