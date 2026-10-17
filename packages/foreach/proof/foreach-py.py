import math
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from foreach.core import ForeachError, RList, RMatrix, TaskError, do, foreach


def fmt(value):
    if isinstance(value, TaskError):
        return "ERR:" + value.message
    if value is None:
        return "NULL"
    if isinstance(value, RMatrix):
        return fmt_matrix(value.data, value.rownames, value.colnames)
    if isinstance(value, np.ndarray) and value.ndim == 2:
        return fmt_matrix(value, None, None)
    if isinstance(value, RList):
        if len(value) == 0:
            return "L()"
        return "L(" + ",".join(fmt(item) for item in value) + ")"
    if isinstance(value, str):
        return "C(" + value + ")"
    if isinstance(value, (list, tuple)):
        if value and all(isinstance(item, str) for item in value):
            return "C(" + ",".join(value) + ")"
        return "V(" + ",".join(format(float(item), ".17g") for item in value) + ")"
    if isinstance(value, (int, float, np.integer, np.floating)):
        return "V(" + format(float(value), ".17g") + ")"
    return "V(" + format(float(value), ".17g") + ")"


def fmt_matrix(data, rownames, colnames):
    vals = ",".join(format(float(item), ".17g") for item in np.ravel(data, order="F"))
    rows = "" if not rownames or all(name is None for name in rownames) else ",".join(rownames)
    cols = "" if not colnames or all(name is None for name in colnames) else ",".join(colnames)
    nrow, ncol = data.shape
    return f"M({nrow},{ncol},{vals};rn={rows};cn={cols})"


def run(fn):
    try:
        return fmt(fn())
    except ForeachError as exc:
        return "ERR:" + exc.message


def drop_two(i):
    if i == 2:
        raise ForeachError("boom")
    return i


def one():
    m = np.arange(1, 10).reshape((3, 3), order="F")
    parts = [
        run(lambda: foreach()),
        run(lambda: foreach(init=0)),
        run(lambda: foreach(i=1, final=1)),
        run(lambda: foreach(i=1, inorder=[True, False])),
        run(lambda: foreach(i=1, maxcombine=1)),
        run(lambda: foreach(i=1, errorhandling="nope")),
        run(lambda: foreach(i=1, errorhandling=("stop", "remove"))),
        run(lambda: foreach(i=1, errorhandling=1)),
        run(lambda: foreach(i=1, packages=1)),
        run(lambda: foreach(i=1, export=1)),
        run(lambda: foreach(i=1, noexport=1)),
        run(lambda: foreach(i=1, verbose=1)),
        run(lambda: foreach(i=1, multicombine=1)),
        run(lambda: foreach(i=1, **{".foo": 1})),
        run(lambda: foreach(i=1, **{".foo": 1, ".bar": 2})),
        run(lambda: foreach(i=1, COMBINE=0)),
        run(lambda: foreach(i=1, COMBINE=0, INIT=1)),
        run(lambda: foreach(i=1, combine="foo")),
        run(lambda: do(foreach(i=[1, 2, 3]), lambda i: math.sqrt(i))),
        run(lambda: do(foreach(i=[1, 2, 3, 4], j=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]), lambda i, j: math.sqrt(i + j))),
        run(lambda: do(foreach(i=[1, 2, 3], combine="c"), lambda i: i)),
        run(lambda: do(foreach(i=[1, 2, 3, 4, 5], combine="+"), lambda i: i)),
        run(lambda: do(foreach(i=[1, 2, 3, 4], combine="*"), lambda i: i)),
        run(lambda: do(foreach(i=[1, 2, 3], combine="cbind"), lambda i: [i, i + 10])),
        run(lambda: do(foreach(i=[1, 2, 3], combine="rbind"), lambda i: [i, i + 10])),
        run(lambda: do(foreach(i=[1, 2, 3, 4], combine="+", init=10), lambda i: i)),
        run(lambda: do(foreach(i=[1, 2, 3], combine="c", final=lambda x: [v * 10 for v in x]), lambda i: i)),
        run(lambda: do(foreach(i=[]), lambda i: i)),
        run(lambda: do(foreach(i=[], combine="c"), lambda i: i)),
        run(lambda: do(foreach(i=1, combine="c"), lambda i: i * 2)),
        run(lambda: do(foreach(i=[1, 2], combine="c"), lambda i: i * 2)),
        run(lambda: do(foreach(i=[1, 2], j=[1, 2, 3, 4, 5], combine="c"), lambda i, j: i + j)),
        run(lambda: do(foreach(i=[1, 2, 3, 4, 5], combine="c", maxcombine=2), lambda i: i)),
        run(lambda: do(foreach(i=[1, 2, 3, 4], combine="+", inorder=False), lambda i: i)),
        run(lambda: do(foreach(i=[1, 2, 3, 4, 5], combine=lambda *args: sum(args), multicombine=True, maxcombine=3), lambda i: i)),
        run(lambda: do(foreach(i=[1, 2, 3, 4, 5], combine=lambda a, b: a + b, multicombine=False), lambda i: i)),
        run(lambda: do(foreach(i=[1, 2, 3, 4], combine="cbind", maxcombine=2), lambda i: [i, i + 10])),
        run(lambda: do(foreach([1, 2, 3], combine="c"), 7)),
        run(lambda: do(foreach(i=[1, 2, 3], combine="c"), lambda i: sum(int(v) for v in m[:, i - 1]) / 3)),
        run(lambda: do(foreach(i=[1, 2, 3, 4], combine="+", multicombine=True), lambda i: i)),
        run(lambda: do(foreach(i=[1, 2, 3, 4], combine="c", errorhandling="rem"), drop_two)),
        run(lambda: do(foreach(i=[1, 2, 3], combine="c", **{".options.snow": {"a": 1}}), lambda i: i)),
        run(lambda: do(foreach(i=[1, 2]), lambda i: [i, i + 10])),
        run(lambda: do(foreach(i=["a", "b"]), lambda i: i)),
        run(lambda: do(foreach(i=[1, 2], combine="c", init=[0]), lambda i: i)),
    ]
    return "|".join(parts)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("VALUE " + value)
print(f"MS {statistics.median(elapsed):.17g}")
