import math
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from iterators.core import IteratorError, iter, nextElem
from iterators.idiv import idiv


def fmt(value):
    value = float(value)
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    return format(value, ".17g")


def err(fn):
    try:
        fn()
        return "OK"
    except IteratorError as exc:
        return exc.message


def take(it, k=16):
    out = []
    for _ in range(k):
        try:
            out.append(fmt(nextElem(it)))
        except IteratorError as exc:
            out.append(exc.message)
            break
    return out


def one():
    p = idiv(10, chunks=3)
    q = idiv(10, chunks=3)
    ind = [nextElem(p), nextElem(q), nextElem(p)]
    base = idiv(10, chunks=2)
    same = "SAME" if iter(base) is base else "DIFF"
    parts = [
        *take(idiv(10, chunks=3)),
        *take(idiv(10, chunkSize=3)),
        *take(idiv(10.5, chunks=3)),
        *take(idiv(10, chunks=2.5)),
        *take(idiv(10, chunkSize=2.5)),
        *take(idiv(5, chunks=4)),
        *take(idiv(2.2, chunkSize=1.1)),
        *take(idiv(7, chunkSize=3)),
        *take(idiv(3, chunkSize=2)),
        *take(idiv(9, chunkSize=4)),
        *take(idiv(1, chunks=3)),
        *take(idiv(10, chunkSize=11)),
        *take(idiv(4, chunkSize=1)),
        *take(idiv(10, chunks=1)),
        *take(idiv(0, chunks=3)),
        *take(idiv(-4, chunks=3)),
        *take(idiv(10, chunks=0)),
        *take(idiv(10, chunks=-2)),
        *take(idiv(10, chunks=0.4)),
        *take(idiv(1e16 + 3, chunks=3)),
        *take(idiv(float("inf"), chunks=3)),
        *take(idiv(float("inf"), chunkSize=3)),
        *take(idiv(10, chunkSize=float("inf"))),
        *take(idiv(float("nan"), chunks=3)),
        *take(idiv(float("nan"), chunkSize=3)),
        *take(idiv(-10, chunkSize=3)),
        *take(idiv(0, chunkSize=3)),
        *take(idiv(-0.0, chunks=3)),
        *[fmt(value) for value in ind],
        same,
        *take(base),
        *take(idiv([10], chunks=3)),
        *take(idiv(10, chunks=[3])),
        *take(idiv(10, chunkSize=[3])),
        *take(idiv(10, chunks=True)),
        *take(idiv(10, chunks=False)),
        *take(idiv(10, chunks="0")),
        *take(idiv(10, chunks="3")),
        *take(idiv(10, chunks=None)),
        *take(idiv(-4, chunks=None)),
        *take(idiv(10, chunks=[])),
        *take(idiv(-4, chunks=[])),
        *take(idiv(10, chunks=[3, 4])),
        *take(idiv(10, chunks=float("nan"))),
        *take(idiv(n=10, chunkSize=3)),
        err(lambda: idiv(10)),
        err(lambda: idiv(10, chunks=3, chunkSize=2)),
        err(lambda: idiv(10, 3)),
        err(lambda: idiv(None, chunks=3)),
        err(lambda: idiv(True, chunks=3)),
        err(lambda: idiv("10", chunks=3)),
        err(lambda: idiv([1, 2], chunks=3)),
        err(lambda: idiv([True], chunks=3)),
        err(lambda: idiv([], chunks=3)),
        err(lambda: idiv(10, chunkSize=0)),
        err(lambda: idiv(10, chunkSize=0.5)),
        err(lambda: idiv(10, chunkSize=-1)),
        err(lambda: idiv(10, chunkSize=float("nan"))),
        err(lambda: idiv(10, chunkSize=float("nan"))),
        err(lambda: idiv(10, chunkSize=None)),
        err(lambda: idiv(10, chunkSize="3")),
        err(lambda: idiv(10, chunkSize=[3, 4])),
        err(lambda: idiv(10, chunkSize=True)),
        err(lambda: idiv(10, chunkSize=float("-inf"))),
        err(lambda: idiv(chunks=3)),
        err(lambda: idiv(10, foo=1, chunks=3)),
        err(lambda: idiv(10, chunksize=3)),
        err(lambda: idiv(10, chunk=3)),
        err(lambda: idiv(10, n=11, chunks=3)),
        err(lambda: idiv(10, 1, chunkSize=0)),
        err(lambda: idiv(True, chunkSize=0)),
        err(lambda: idiv("x", chunks=3, chunkSize=1)),
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
