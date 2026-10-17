import math
import statistics
import sys
import time
import warnings

warnings.filterwarnings("ignore")
import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/zoo")
from zoo.plot import make_par_list


def fmt_one(value):
    if value is None:
        return "null"
    if isinstance(value, str):
        return value
    number = float(value)
    if math.isnan(number):
        return "NA"
    if math.isinf(number):
        return "Inf" if number > 0 else "-Inf"
    return format(number, ".16g")


def fmt_val(value):
    if value is None:
        return "null"
    if isinstance(value, str):
        return value
    if isinstance(value, np.ndarray):
        return "|".join(fmt_one(item) for item in value.reshape(-1))
    if isinstance(value, (list, tuple)):
        return "|".join(fmt_one(item) for item in value)
    return fmt_one(value)


def fmt_par(rows):
    return "\n".join(f"{name}: {fmt_val(value)}" for name, value in rows)


def one():
    names = ["A", "B", "C"]
    parts = [
        "CASE named-unnamed\n" + fmt_par(make_par_list(names, [("A", [1, 2]), ("", [3, 4])], 5, 3, 1)),
        "CASE named-only\n" + fmt_par(make_par_list(names, {"B": 2}, 5, 3, 1)),
        "CASE atomic-multi\n" + fmt_par(make_par_list(names, [1, 2, 3], 4, 3, 9)),
        "CASE atomic-single\n" + fmt_par(make_par_list(["A"], [1, 2, 3], 5, 1, 9)),
        "CASE scalar-multi\n" + fmt_par(make_par_list(names, 7, 4, 3, 9)),
        "CASE mixed-list\n" + fmt_par(make_par_list(names, [("C", 4), ("", 2)], 3, 3, 1)),
        "CASE pch-partial\n" + fmt_par(make_par_list(names, [("A", [1, 2, 3, 4, 5]), ("B", 3)], 5, 3, 1)),
        "CASE recycle-false-unnamed\n"
        + fmt_par(make_par_list(names, [("A", 8), ("", 3), ("", 4)], 2, 3, 0, recycle=False)),
        "CASE def-vector\n" + fmt_par(make_par_list(names, [("A", 5)], 3, 3, [1, 2], recycle=False)),
        "CASE empty-numeric\n"
        + fmt_par(make_par_list(["A", "B"], [("A", np.array([])), ("", 5)], 3, 2, 1)),
        "CASE null-def\n" + fmt_par(make_par_list(names, [("A", [0, 1])], 2, 3, None)),
    ]
    try:
        make_par_list(names, {"A": 1, "B": 2}, 2, 3, 0, recycle=True)
        err = "NO ERROR"
    except ValueError as exc:
        err = str(exc)
    parts.append("CASE error-recycle\nERROR " + err)
    return "\n\n".join(parts)


value = one()
out = "/home/ahmed/killr_projects/killr/packages/zoo/docs/output/make.par.list-python.txt"
with open(out, "w", encoding="utf-8") as handle:
    handle.write(value + "\n")
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("%.17g" % statistics.median(elapsed))
