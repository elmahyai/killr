
import statistics
import time
import warnings

import numpy as np

warnings.simplefilter("ignore")

from tseries.arma import arma
from tseries.datasets import tcm


def cell(value):
    if isinstance(value, (bool, np.bool_)):
        return "TRUE" if bool(value) else "FALSE"
    if isinstance(value, float):
        if value != value:
            return "NaN"
        return format(value, ".17g")
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    return str(value)


def join(values):
    return ",".join(cell(value) for value in np.ravel(values))


def one():
    r = np.diff(tcm().values[:, 3])
    fit = arma(r, order=(1, 1))
    return join(fit["coef"]) + "|" + cell(fit["css"])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value)
print(statistics.median(elapsed))
