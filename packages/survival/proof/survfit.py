import math
import statistics
import time

import numpy as np
from survival.strata import StrataFactor
from survival.surv import SurvObject
from survival.survfit import survfit

N = 240
TIME = [((i * 17) % 80) + 1 for i in range(1, N + 1)]
LABELS = ["censor", "death", "pcm"]
STATUS = [{"censor": 0, "death": 1, "pcm": 2}[LABELS[i % 3]] for i in range(1, N + 1)]
Y = SurvObject(
    np.column_stack([TIME, STATUS]),
    "mright",
    ["death", "pcm"],
    "censor",
)
ONE = StrataFactor([1] * N, ["1"])
GROUP = StrataFactor(
    [1 if i % 2 == 0 else 2 for i in range(1, N + 1)],
    ["group=A", "group=B"],
)


def flat(value):
    if isinstance(value, (bool, np.bool_)):
        return [float(value)]
    return np.asarray(value, dtype=float).ravel(order="F").tolist()


def nums(fit):
    out = []
    for key in (
        "n",
        "time",
        "n.risk",
        "n.event",
        "n.censor",
        "pstate",
        "n.transition",
        "n.id",
        "cumhaz",
        "std.err",
        "std.chaz",
        "std.auc",
        "lower",
        "upper",
        "strata",
        "p0",
        "logse",
        "conf.int",
        "t0",
        "transitions",
    ):
        if key in fit and fit[key] is not None:
            out.extend(flat(fit[key]))
    return out


def meta_one(fit):
    strata = fit.get("strata.names")
    return [
        "-" if not strata else ",".join(strata),
        str(fit["type"]),
        "-" if "conf.type" not in fit else str(fit["conf.type"]),
        ",".join(fit["states"]),
        ",".join(fit["cumhaz.names"]),
    ]


def one():
    fits = [survfit(ONE, Y), survfit(GROUP, Y)]
    numbers = []
    meta = []
    for fit in fits:
        numbers.extend(nums(fit))
        meta.extend(meta_one(fit))
    return numbers, meta


def fmt(value):
    if isinstance(value, str):
        return value
    number = float(value)
    if math.isnan(number):
        return "NA"
    if math.isinf(number):
        return "Inf" if number > 0 else "-Inf"
    return f"{number:.17g}"


value, meta = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(fmt(item) for item in value))
print("META")
print("\n".join(meta))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
