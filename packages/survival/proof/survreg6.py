import json
import statistics
import sys
from pathlib import Path

import numpy as np

# This file is named survreg6.py, so drop its directory before importing the crate.
_here = Path(__file__).resolve().parent
sys.path = [p for p in sys.path if Path(p).resolve() != _here]
from survreg6 import survreg6, survreg6_timed

# Same three Csurvreg6 inputs as survreg6.R. y and covar are column-major.


def f64(values):
    return np.ascontiguousarray(values, dtype=np.float64)


def i32(values):
    return np.ascontiguousarray(values, dtype=np.int32)


def col_major(columns):
    mat = np.column_stack(columns)
    return np.ascontiguousarray(mat.ravel(order="F"))


n = 2000
idx = np.arange(1, n + 1)
x1 = ((idx * 17) % 10) / 10
x2 = ((idx * 13) % 7).astype(float) - 3
time = 0.3 + ((idx * 31) % 50) / 10
status = np.where(idx % 5 == 0, 0.0, 1.0)
y_main = col_major([np.log(time), status])
x_main = col_major([np.ones(n), x1, x2])
wt_main = f64(1 + (idx % 3) * 0.5)
off_main = f64(((idx % 4) - 1) * 0.05)
beta_main = f64([3, 1, -1, -1])
strata_main = i32(np.ones(n, dtype=np.int32))

n2 = 40
idx2 = np.arange(1, n2 + 1)
time2 = 20 + (idx2 % 15)
status2 = np.where(idx2 % 4 == 0, 2.0, 1.0)
y_g = col_major([time2.astype(float), status2])
x_g = col_major([np.ones(n2), (idx2 % 5) - 2])
beta_g = f64([25, 0.5, np.log(4)])
strata_g = i32(np.ones(n2, dtype=np.int32))
ones2 = f64(np.ones(n2))
zero2 = f64(np.zeros(n2))

n3 = 36
idx3 = np.arange(1, n3 + 1)
t1 = 1 + (idx3 % 8)
t2 = t1 + 1 + (idx3 % 3)
status3 = np.where(idx3 % 3 == 0, 3.0, np.where(idx3 % 3 == 1, 1.0, 0.0))
y_l = col_major([t1.astype(float), t2.astype(float), status3])
x_l = col_major([np.ones(n3), (idx3 % 2) * 2 - 1])
strata_l = i32(np.where(idx3 <= 18, 1, 2))
beta_l = f64([4, 0.3, np.log(1.5), np.log(2)])
ones3 = f64(np.ones(n3))
zero3 = f64(np.zeros(n3))


def pack(coef, loglik, u, var, iter_, flag):
    return [float(v) for v in coef] + [float(loglik)] + [float(v) for v in u] + [
        float(v) for v in var
    ] + [float(iter_), float(flag)]


def run(timed):
    call = survreg6_timed if timed else survreg6
    ms = 0.0
    out = []
    specs = [
        (30, 3, y_main, 2, x_main, wt_main, off_main, beta_main, 1, strata_main, 1e-9, 1e-10, 1),
        (30, 2, y_g, 2, x_g, ones2, zero2, beta_g, 0, strata_g, 1e-9, 1e-10, 3),
        (30, 2, y_l, 3, x_l, ones3, zero3, beta_l, 2, strata_l, 1e-9, 1e-10, 2),
    ]
    for spec in specs:
        result = call(*spec)
        if timed:
            coef, iter_, var, loglik, flag, u, dt = result
            ms += dt
        else:
            coef, iter_, var, loglik, flag, u = result
        out.extend(pack(coef, loglik, u, var, iter_, flag))
    return out, ms


value, _ = run(False)
elapsed = []
for _ in range(20):
    _, ms = run(True)
    elapsed.append(ms)
print(json.dumps({"values": value, "median_ms": statistics.median(elapsed)}))
