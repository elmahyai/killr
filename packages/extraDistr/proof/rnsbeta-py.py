import time

import numpy as np
from boot.rng import set_seed

from extradistr.continuous import rnsbeta


def one():
    return rnsbeta(4, 5, 13, -4, 8)


def fmt(value):
    text = []
    for item in np.asarray(value, dtype=float).reshape(-1):
        if np.isnan(item):
            text.append("NaN")
        elif np.isposinf(item):
            text.append("Inf")
        elif np.isneginf(item):
            text.append("-Inf")
        else:
            text.append(format(float(item), ".17g"))
    return ",".join(text)


set_seed(1)
value = one()
elapsed = []
for _ in range(20):
    set_seed(1)
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(fmt(value))
print(format(float(np.median(elapsed)), ".17g"))
