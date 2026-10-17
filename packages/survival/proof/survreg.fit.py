import statistics
import sys
import time
from pathlib import Path

import numpy as np

# proof/survreg6.py would shadow the survreg6 crate, so drop this directory first.
_here = Path(__file__).resolve().parent
sys.path = [p for p in sys.path if Path(p).resolve() != _here]

from survival.control import survreg_control  # noqa: E402
from survival.survreg_fit import survreg_fit

# Same three survreg.fit calls as survreg.fit.R.
ctrl = survreg_control()


def pack(fit):
    return (
        list(np.ravel(fit["coefficients"]))
        + list(np.ravel(fit["icoef"]))
        + list(np.ravel(fit["var"], order="F"))
        + list(np.ravel(fit["loglik"]))
        + [fit["iter"]]
        + list(np.ravel(fit["linear.predictors"]))
        + [fit["df"]]
        + list(np.ravel(fit["score"]))
    )


n = 2000
idx = np.arange(1, n + 1)
x1 = ((idx * 17) % 10) / 10
x2 = ((idx * 13) % 7).astype(float) - 3
time_main = 0.3 + ((idx * 31) % 50) / 10
status = np.where(idx % 5 == 0, 0.0, 1.0)
y_main = np.column_stack([np.log(time_main), status])
x_main = np.column_stack([np.ones(n), x1, x2])
wt_main = 1 + (idx % 3) * 0.5
off_main = ((idx % 4) - 1) * 0.05
strata_main = np.ones(n, dtype=np.int32)

n2 = 40
idx2 = np.arange(1, n2 + 1)
time2 = (20 + (idx2 % 15)).astype(float)
status2 = np.where(idx2 % 4 == 0, 2.0, 1.0)
y_g = np.column_stack([time2, status2])
x_g = np.column_stack([np.ones(n2), (idx2 % 5) - 2.0])

n3 = 36
idx3 = np.arange(1, n3 + 1)
t1 = (1 + (idx3 % 8)).astype(float)
t2 = t1 + 1 + (idx3 % 3)
status3 = np.where(idx3 % 3 == 0, 3.0, np.where(idx3 % 3 == 1, 1.0, 0.0))
y_l = np.column_stack([t1, t2, status3])
x_l = np.column_stack([np.ones(n3), (idx3 % 2) * 2.0 - 1.0])
strata_l = np.where(idx3 <= 18, 1, 2).astype(np.int32)


def one():
    a = survreg_fit(
        x_main, y_main, weights=wt_main, offset=off_main, init=None,
        controlvals=ctrl, dist="extreme", scale=0, nstrat=1, strata=strata_main,
    )
    b = survreg_fit(
        x_g, y_g, weights=None, offset=None, init=None,
        controlvals=ctrl, dist="gaussian", scale=4, nstrat=1,
    )
    c = survreg_fit(
        x_l, y_l, weights=None, offset=None, init=None,
        controlvals=ctrl, dist="logistic", scale=0, nstrat=2, strata=strata_l,
    )
    return pack(a) + pack(b) + pack(c)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(f"{float(v):.17g}" for v in value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
