import math
import statistics
import time

import numpy as np
from survival.strata import StrataFactor
from survival.surv import Surv
from survival.survfit_km import survfitKM


AML_TIME = [9, 13, 13, 18, 23, 28, 31, 34, 45, 48, 161, 5, 5, 8, 8, 12, 16, 23, 27, 30, 33, 43, 45]
AML_STATUS = [1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1]
AML_X = ["Maintained"] * 11 + ["Nonmaintained"] * 12


def r_factor(values, levels=None):
    labels = [str(value) for value in values]
    if levels is None:
        levels = sorted(set(labels))
    index = {level: code for code, level in enumerate(levels, start=1)}
    return StrataFactor([index[label] for label in labels], list(levels))


def one_level(n):
    return StrataFactor([1] * n, ["1"])


aml_y = Surv(AML_TIME, AML_STATUS)
aml_x = r_factor(AML_X)

N_SYN = 180
syn_time = [((i * 17) % 97) + 1 for i in range(1, N_SYN + 1)]
syn_status = [int(i % 5 != 0) for i in range(1, N_SYN + 1)]
syn_grp = r_factor([["a", "b", "c"][i % 3] for i in range(1, N_SYN + 1)])
syn_y = Surv(syn_time, syn_status)

CT_START = [0, 5, 0, 0, 3]
CT_STOP = [5, 12, 4, 8, 9]
CT_STATUS = [0, 1, 1, 0, 1]
CT_ID = [1, 1, 2, 3, 3]
CT_GRP = r_factor(["a", "a", "b", "a", "b"], ["a", "b"])
ct_y = Surv(CT_START, CT_STOP, CT_STATUS)


def flat(value):
    if value is None:
        return []
    if isinstance(value, list):
        out = []
        for item in value:
            out.extend(np.asarray(item, dtype=float).ravel(order="F").tolist())
        return out
    return np.asarray(value, dtype=float).ravel(order="F").tolist()


def nums(fit):
    out = []
    for key in (
        "n",
        "time",
        "n.risk",
        "n.event",
        "n.censor",
        "surv",
        "std.err",
        "cumhaz",
        "std.chaz",
        "lower",
        "upper",
        "strata",
        "n.enter",
        "counts",
        "n.id",
        "logse",
        "conf.int",
        "t0",
        "influence.surv",
        "influence.chaz",
    ):
        if key in fit and fit[key] is not None:
            out.extend(flat(fit[key]))
    return out


def rn_one(names):
    if names and isinstance(names[0], list):
        return ";".join(",".join(group) for group in names)
    return ",".join(names)


def meta_one(fit):
    bits = []
    for key in ("influence.surv.rownames", "influence.chaz.rownames"):
        names = fit.get(key)
        if names is not None:
            bits.append(rn_one(names))
    rn = "|".join(bits) if bits else "-"
    strata = fit.get("strata.names")
    return [
        "-" if not strata else ",".join(strata),
        str(fit["type"]),
        "-" if "conf.type" not in fit else str(fit["conf.type"]),
        "-" if "conf.lower" not in fit else str(fit["conf.lower"]),
        rn,
    ]


def one():
    fits = [
        survfitKM(one_level(len(AML_TIME)), aml_y),
        survfitKM(aml_x, aml_y),
        survfitKM(one_level(len(AML_TIME)), aml_y, type="fh2"),
        survfitKM(aml_x, aml_y, ctype=2, conf_lower="modified"),
        survfitKM(one_level(len(AML_TIME)), aml_y, weights=[1 + (i % 2) for i in range(1, len(AML_TIME) + 1)]),
        survfitKM(
            one_level(len(AML_TIME)),
            aml_y,
            cluster=[(i % 4) + 1 for i in range(1, len(AML_TIME) + 1)],
            influence=3,
        ),
        survfitKM(
            one_level(len(AML_TIME)),
            aml_y,
            start_time=30,
            weights=[1.0] * len(AML_TIME),
            id=list(range(1, len(AML_TIME) + 1)),
        ),
        survfitKM(one_level(5), ct_y, id=CT_ID),
        survfitKM(CT_GRP, ct_y, id=CT_ID, entry=True),
        survfitKM(syn_grp, syn_y),
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
        return "NaN"
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
