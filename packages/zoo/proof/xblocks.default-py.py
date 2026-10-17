import math
import statistics
import sys
import time
import warnings

warnings.filterwarnings("ignore")
import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/zoo")
from zoo.plot import xblocks_default


def fmt_one(value):
    if value is None:
        return "NA"
    if isinstance(value, str):
        return value
    if isinstance(value, (bool, np.bool_)):
        return "TRUE" if bool(value) else "FALSE"
    number = float(value)
    if math.isnan(number):
        return "NA"
    if math.isinf(number):
        return "Inf" if number > 0 else "-Inf"
    return format(number, ".16g")


def fmt_vec(value):
    if value is None:
        return "null"
    return "|".join(fmt_one(item) for item in list(value))


def block_text(name, rec):
    if rec is None:
        return f"CASE {name}\nEMPTY"
    border = rec["border"]
    return "\n".join(
        [
            f"CASE {name}",
            "left=" + fmt_vec(rec["left"]),
            "right=" + fmt_vec(rec["right"]),
            "bottom=" + fmt_one(rec["bottom"]),
            "top=" + fmt_one(rec["top"]),
            "col=" + fmt_vec(rec["col"]),
            "border=" + ("NA" if border is None else str(border)),
        ]
    )


def one():
    parts = [
        block_text(
            "logical",
            xblocks_default(
                [1, 2, 4, 7, 8],
                [True, True, False, True, None],
                col=["red", "blue"],
                ybottom=0,
                ytop=1,
                draw=False,
            ),
        ),
        block_text(
            "numeric",
            xblocks_default([1, 2, 3, 4, 5], [1, None, None, 3, 4], ybottom=0, ytop=1, draw=False),
        ),
        block_text(
            "character",
            xblocks_default([1, 2, 3, 4], ["red", "red", "blue", None], ybottom=0, ytop=1, draw=False),
        ),
        block_text(
            "override",
            xblocks_default(
                [1, 2, 3, 4],
                ["red", "red", "blue", "blue"],
                col=["green", "gold"],
                ybottom=0,
                ytop=1,
                draw=False,
            ),
        ),
        block_text(
            "function",
            xblocks_default(
                list(range(1, 7)),
                lambda t: np.asarray(t) > 3,
                col="gray",
                ybottom=0,
                ytop=1,
                border="slategray",
                draw=False,
            ),
        ),
        block_text("length-one", xblocks_default([5], [True], ybottom=0, ytop=1, draw=False)),
        block_text(
            "log",
            xblocks_default(
                list(range(1, 6)),
                [True, False, True, True, False],
                ybottom=0.84,
                ytop=5.16,
                ylog=True,
                draw=False,
            ),
        ),
        block_text(
            "na-x",
            xblocks_default([1, None, 3], [True, True, False], ybottom=0, ytop=1, draw=False),
        ),
        block_text("empty", xblocks_default([], [], draw=False)),
    ]
    try:
        xblocks_default([1, 3, 2], [True, True, False], ybottom=0, ytop=1, draw=False)
        err = "NO ERROR"
    except ValueError as exc:
        err = str(exc)
    parts.append("CASE unsorted\nERROR " + err)
    return "\n\n".join(parts)


value = one()
out = "/home/ahmed/killr_projects/killr/packages/zoo/docs/output/xblocks.default-python.txt"
with open(out, "w", encoding="utf-8") as handle:
    handle.write(value + "\n")
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("%.17g" % statistics.median(elapsed))
