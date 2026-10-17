import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/xtable")

from xtable.align_replacement import align_replacement
from xtable.caption_replacement import Xtable
from xtable.digits_replacement import digits_replacement
from xtable.display_replacement import display_replacement
from xtable.to_latex import to_latex_xtable


def make_x1():
    x = Xtable(
        [[1, 1.5, "a"], [2, 2.0, "b"], [3, 3.1, "c"]],
        col_names=["a", "b", "c"],
        row_names=["1", "2", "3"],
    )
    x = align_replacement(x, ["l", "r", "r", "l"])
    x = digits_replacement(x, [0, 0, 1, 0])
    x = display_replacement(x, ["s", "d", "f", "s"])
    return x


def make_x2():
    x = Xtable(
        [[1, 1.5], [2, 2.0]],
        col_names=["a", "b"],
        row_names=["1", "2"],
    )
    x = align_replacement(x, ["r", "r", "r"])
    x = digits_replacement(x, [0, 0, 1])
    x = display_replacement(x, ["s", "d", "f"])
    return x


def make_x3():
    x = Xtable(
        [[0.12, "a&b"], [1.2, "c>d"]],
        col_names=["x", "y"],
        row_names=["1", "2"],
    )
    x = align_replacement(x, ["l", "r", "l"])
    x = digits_replacement(x, [0, 2, 0])
    x = display_replacement(x, ["s", "f", "s"])
    return x


def one():
    return {
        "basic": to_latex_xtable(make_x1(), comment=False, floating=False),
        "no_row": to_latex_xtable(
            make_x2(), comment=False, floating=False, **{"include.rownames": False}
        ),
        "sanitize": to_latex_xtable(make_x3(), comment=False, floating=False),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"median_ms": statistics.median(elapsed), "value": value}))
