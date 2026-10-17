import math
import statistics
import time

import numpy as np
from survival.fromtimeline import Categorical
from survival.survfit_formula import survfit_formula

N = 240
IDX = range(1, N + 1)
TIME = [((i * 17) % 80) + 1 for i in IDX]
STATUS01 = [1.0 if i % 4 != 0 else 0.0 for i in IDX]
STATUS = Categorical(
    [["censor", "death", "pcm"][i % 3] for i in IDX],
    ["censor", "death", "pcm"],
)
GROUP = [None if i % 50 == 0 else ("A" if i % 2 == 0 else "B") for i in IDX]
SITE = [["north", "east", "south"][i % 3] for i in IDX]
W = [1 + (i % 3) * 0.5 for i in IDX]
KEEP = [i % 7 != 0 for i in IDX]
START = [t // 4 for t in TIME]
PID = [(i % 60) + 1 for i in IDX]
DATA = {
    "time": TIME,
    "status01": STATUS01,
    "status": STATUS,
    "group": GROUP,
    "site": SITE,
    "w": W,
    "keep": KEEP,
    "start": START,
    "pid": PID,
}


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
        "n.enter",
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
        "counts",
        "na.action",
    ):
        if key in fit and fit[key] is not None:
            out.extend(flat(fit[key]))
    return out


def meta_one(fit):
    strata = fit.get("strata.names")
    states = fit.get("states")
    cumhaz = fit.get("cumhaz.names")
    return [
        "-" if not strata else ",".join(strata),
        str(fit["type"]),
        "-" if "conf.type" not in fit else str(fit["conf.type"]),
        "-" if states is None else ",".join(states),
        ",".join(cumhaz or []),
    ]


def one():
    fits = [
        survfit_formula("Surv(time, status01) ~ 1", DATA),
        survfit_formula("Surv(time, status01) ~ group", DATA),
        survfit_formula("Surv(time, status01) ~ group + site", DATA),
        survfit_formula("Surv(time, status01) ~ strata(site)", DATA),
        survfit_formula("Surv(time, status) ~ group", DATA),
        survfit_formula("Surv(start, time, status01) ~ group", DATA, entry=True),
        survfit_formula("Surv(start, time, status01) ~ group", DATA),
        survfit_formula("Surv(time, status01) ~ group", DATA, weights="w"),
        survfit_formula("Surv(time, status01) ~ group", DATA, subset=KEEP),
        survfit_formula("Surv(time, status01) ~ group", DATA, conf_type="log-log", conf_int=0.9),
        survfit_formula("Surv(time, status01) ~ site", DATA, id=PID, stype=2, ctype=2),
        survfit_formula("Surv(time, status01) ~ 1", DATA, start_time=20),
    ]
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
