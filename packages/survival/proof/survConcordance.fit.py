import statistics
import time
import warnings

import numpy as np

from survival.surv import Surv
from survival.survConcordance_fit import survConcordance_fit


def fmt(x):
    if x is None:
        return "NULL"
    flat = np.asarray(x, dtype=float).reshape(-1)
    parts = []
    for v in flat:
        if np.isnan(v):
            parts.append("NA")
        else:
            parts.append(f"{v:.17g}")
    return ",".join(parts)


def one():
    time_ = [1, 2, 2, 2, 3, 4, 4, 4, 5, 2]
    status = [1, 0, 1, 0, 1, 0, 1, 1, 0, 1]
    x = [5, 5, 4, 4, 3, 3, 7, 6, 5, 4]
    s = ["a", "a", "b", "b", "a", "b", "a", "b", "a", "b"]
    w = [1, 2, 1, 1, 2, 1, 1, 0.5, 1, 1]
    start = [0, 0, 1, 2, 0, 3, 1, 2, 0, 4]
    stop = [2, 3, 4, 4, 5, 6, 6, 7, 8, 9]
    cstatus = [1, 0, 1, 1, 0, 1, 0, 1, 1, 0]
    xc = [3, 5, 2, 4, 1, 5, 3, 2, 4, 1]
    cs = ["u", "v", "u", "v", "u", "u", "v", "v", "u", "v"]
    y = Surv(time_, status)
    yc = Surv(start, stop, cstatus, type="counting")
    r1 = survConcordance_fit(y, x)
    r2 = survConcordance_fit(y, x, s)
    r3 = survConcordance_fit(y, x, weight=w)
    r4 = survConcordance_fit(yc, xc)
    r5 = survConcordance_fit(yc, xc, cs)
    return [
        fmt(r1),
        fmt(np.asarray(r2).reshape(-1)),
        fmt(r3),
        fmt(r4),
        fmt(np.asarray(r5).reshape(-1)),
    ]


with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    value = one()
    elapsed = []
    for _ in range(20):
        started = time.perf_counter()
        one()
        elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
