import statistics
import time

import numpy as np

from boot.importance import imp_quantile


def load(path="/tmp/boot-importance-check.bin"):
    with open(path, "rb") as handle:
        header = np.fromfile(handle, dtype="<i4", count=7)
        n, n_r, n_t_row, n_t_col, n_t0, n_w_row, n_w_col = (int(value) for value in header)
        data = np.fromfile(handle, dtype="<f8", count=n)
        strata = np.fromfile(handle, dtype="<f8", count=n)
        replicates = np.fromfile(handle, dtype="<i4", count=n_r)
        t0 = np.fromfile(handle, dtype="<f8", count=n_t0)
        t = np.fromfile(handle, dtype="<f8", count=n_t_row * n_t_col).reshape(n_t_row, n_t_col)
        weights = np.fromfile(handle, dtype="<f8", count=n_w_row * n_w_col).reshape(n_w_row, n_w_col)
        n_rep = int(replicates.sum())
        frequency = np.fromfile(handle, dtype="<f8", count=n_rep * n).reshape(n_rep, n)
    return {
        "data": data,
        "strata": strata,
        "R": replicates,
        "t0": t0,
        "t": t,
        "weights": weights,
        "frequency": frequency,
    }


boot_out = load()


def one():
    imp_quantile(boot_out)


one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("%.17g" % statistics.median(elapsed))
