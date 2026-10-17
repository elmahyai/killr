import statistics
import time
import warnings

import numpy as np
from scipy.special import expit

from survival._yates_mm import YatesError
from survival.yates_setup import yates_setup

CFIT = {"class": ["coxph"]}
GFIT = {"class": ["glm", "lm"], "family": {"linkinv": expit}}
LFIT = {"class": ["lm"]}
ETA = np.linspace(-2, 2, 9)


def fmt(x):
    if x is None:
        return ["NULL"]
    if isinstance(x, str):
        return [x]
    return [f"{float(v):.17g}" for v in np.atleast_1d(np.asarray(x, dtype=float))]


def err(fn):
    try:
        fn()
    except YatesError as exc:
        return f"error: {exc}"
    return "error: none"


def one():
    out = []
    out += fmt(yates_setup(CFIT))
    out += fmt(yates_setup(CFIT, predict="linear"))
    out += fmt(yates_setup(CFIT, predict="risk")(ETA, None))
    out.append(err(lambda: yates_setup(CFIT, predict="terms")))
    out += fmt(yates_setup(GFIT))
    out += fmt(yates_setup(GFIT, predict="response")(ETA, None))
    out.append(err(lambda: yates_setup(GFIT, predict="terms")))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        val = yates_setup(LFIT, "response")
    out += fmt(val)
    out.append("warning: " + (str(caught[0].message) if caught else ""))
    return out


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
