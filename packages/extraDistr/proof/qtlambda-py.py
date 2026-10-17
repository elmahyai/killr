import time

import numpy as np

from extradistr.continuous import qtlambda


def one():
    return qtlambda([0.1, 0.25, 0.5, 0.8], 0.14)


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


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(fmt(value))
print(format(float(np.median(elapsed)), ".17g"))
