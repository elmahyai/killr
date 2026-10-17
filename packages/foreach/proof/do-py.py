import math
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from foreach.core import ForeachError, RList, RMatrix, TaskError, do, foreach
from iterators.core import icount, iter


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


def boom(i):
    if i == 2:
        raise ForeachError("boom")
    return i


def nope(i):
    if i == 3:
        raise ForeachError("nope")
    return i


def stop_a(_i):
    raise ForeachError("a")


def drop_first(i):
    if i == 1:
        raise ForeachError("a")
    return i


def one():
    m = np.arange(1, 7).reshape((2, 3), order="F")
    k = 10
    parts = [
        run(lambda: do(foreach(i=[1, 2, 3]), lambda i: math.sqrt(i))),
        run(lambda: do(foreach(i=[1, 2, 3], combine="c"), lambda i: math.sqrt(i))),
        run(lambda: do(foreach(i=[1, 2, 3]), boom)),
        run(lambda: do(foreach(i=[1, 2, 3, 4], errorhandling="remove", combine="c"), boom)),
        run(lambda: do(foreach(i=[1, 2, 3], errorhandling="pass"), boom)),
        run(lambda: do([1, 2, 3], 1)),
        run(lambda: do(foreach(col=iter(m, by="col"), combine="cbind"), lambda col: col)),
        run(lambda: do(foreach(row=iter(m, by="row"), combine="rbind"), lambda row: row)),
        run(lambda: do(foreach(i=[1, 2, 3], combine="c"), lambda i: i + k)),
        run(lambda: do(foreach(i=[1, 2, 3, 4], combine="c"), nope)),
        run(lambda: do(foreach(i=[1, 2], errorhandling="remove", combine="c"), stop_a)),
        run(lambda: do(foreach(i=[1, 2], errorhandling="remove"), stop_a)),
        run(lambda: do(foreach(i=[1, 2, 3], errorhandling="remove", combine="c"), drop_first)),
        run(lambda: do(foreach(i=[], combine="c", final=lambda x: 0 if x is None else len(x)), lambda i: i)),
        run(lambda: do(foreach(i=[1, 2, 3, 4], combine="c", final=sum), lambda i: i)),
        run(lambda: do(foreach(icount(2), icount(5), combine="c"), 9)),
        run(lambda: do(foreach(icount(2), j=[10, 11, 12], combine="c"), lambda j: j)),
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
