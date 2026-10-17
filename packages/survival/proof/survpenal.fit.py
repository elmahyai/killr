import statistics
import sys
import time
from pathlib import Path

import numpy as np

# proof/ridge.py would shadow the survival ridge module, so drop this directory first.
_here = Path(__file__).resolve().parent
sys.path = [p for p in sys.path if Path(p).resolve() != _here]

from survival.control import survreg_control  # noqa: E402
from survival.ridge import ridge  # noqa: E402
from survival.survpenal_fit import survpenal_fit  # noqa: E402

# Same survpenal.fit call as survpenal.fit.R.
ctrl = survreg_control()


def pack(fit):
    return (
        list(np.ravel(fit["coefficients"]))
        + list(np.ravel(fit["var"], order="F"))
        + list(np.ravel(fit["var2"], order="F"))
        + list(np.ravel(fit["loglik"]))
        + list(np.ravel(fit["iter"]))
        + list(np.ravel(fit["linear.predictors"]))
        + list(np.ravel(fit["df"]))
        + list(np.ravel(fit["penalty"]))
        + list(np.ravel(fit["score"]))
    )


# ridge() names its columns from the caller's variable names, so x1 and x2 are module level.
n = 200
idx = np.arange(1, n + 1)
x1 = ((idx * 17) % 10) / 10
x2 = ((idx * 13) % 7).astype(float) - 3
x3 = ((idx * 7) % 5) / 5
event_time = 0.5 + ((idx * 31) % 50) / 10
status = np.where(idx % 4 == 0, 0.0, 1.0)
y = np.column_stack([np.log(event_time), status])
x = np.column_stack([np.ones(n), x1, x2, x3])
assign = {"(Intercept)": [1], "ridge(x1, x2)": [2, 3], "x3": [4]}


def one():
    fit = survpenal_fit(
        x, y, weights=None, offset=None, init=None,
        controlvals=ctrl, dist="extreme", scale=0, nstrat=1,
        pcols=[[2, 3]], pattr=[ridge(x1, x2)], assign=assign,
    )
    return pack(fit)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(f"{float(v):.17g}" for v in value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
