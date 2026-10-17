import statistics
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

# proof/survreg6.py would shadow the survreg6 crate, so drop this directory first.
_here = Path(__file__).resolve().parent
sys.path = [p for p in sys.path if Path(p).resolve() != _here]

from survival.control import survreg_control  # noqa: E402
from survival.survreg import survreg  # noqa: E402

# Same four survreg() calls as survreg.R.
ctrl = survreg_control()


def pack(fit):
    na = [] if "na.action" not in fit else [int(i) + 1 for i in np.ravel(fit["na.action"])]
    out = [float(len(na))] + [float(i) for i in na]
    out += list(np.ravel(fit["coefficients"]))
    out += list(np.ravel(fit["icoef"]))
    out += list(np.ravel(fit["var"], order="F"))
    out += list(np.ravel(fit["loglik"]))
    out += [float(fit["iter"])]
    out += list(np.ravel(fit["linear.predictors"]))
    out += [float(fit["df.residual"])]
    out += [float(fit["idf"])]
    out += list(np.ravel(fit["scale"]))
    out += list(np.ravel(fit["means"]))
    out += list(np.ravel(fit["y"], order="F"))
    return out


n = 300
idx = np.arange(1, n + 1)
x1 = ((idx * 17) % 10) / 10.0
x1[idx % 37 == 0] = np.nan
x2 = ((idx * 13) % 7).astype(float) - 3
g = np.array(["alpha", "beta", "gamma"])[idx % 3]
surv_time = 0.3 + ((idx * 31) % 50) / 10
status = np.where(idx % 5 == 0, 0.0, 1.0)
off = ((idx % 4) - 1) * 0.05
wt = 1 + (idx % 3) * 0.5
df = pd.DataFrame(
    {"time": surv_time, "status": status, "x1": x1, "x2": x2, "g": g, "off": off, "wt": wt}
)


def one():
    a = survreg(
        "Surv(time, status) ~ x1 + x2", data=df, weights="wt", dist="extreme", control=ctrl
    )
    b = survreg(
        "Surv(time, status) ~ g + x1 + offset(off)", data=df, dist="extreme", control=ctrl
    )
    c = survreg(
        "Surv(time, status) ~ x2 + strata(g)", data=df, dist="extreme", control=ctrl
    )
    d = survreg("Surv(time, status) ~ x2", data=df, dist="weibull", control=ctrl)
    return pack(a) + pack(b) + pack(c) + pack(d)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(f"{float(v):.17g}" for v in value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
