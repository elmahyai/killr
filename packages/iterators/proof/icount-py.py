import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from iterators.core import IteratorError, icount, nextElem


def err(fn):
    try:
        fn()
        return "OK"
    except IteratorError as exc:
        return exc.message


def one():
    it = icount(3)
    a = [nextElem(it), nextElem(it), nextElem(it)]
    e1 = err(lambda: nextElem(it))
    it = icount(2.5)
    b = [nextElem(it), nextElem(it), nextElem(it)]
    e2 = err(lambda: nextElem(it))
    it = icount()
    c0 = [nextElem(it), nextElem(it)]
    e3 = err(lambda: icount(None))
    e4 = err(lambda: icount([1, 2]))
    e5 = err(lambda: icount(True))
    it = icount(float("nan"))
    e6 = err(lambda: nextElem(it))
    it = icount(0)
    e7 = err(lambda: nextElem(it))
    it = icount(-3)
    e8 = err(lambda: nextElem(it))
    it = icount(1)
    onev = nextElem(it)
    e9 = err(lambda: nextElem(it))
    p = icount(2)
    q = icount(2)
    ind = [nextElem(p), nextElem(q), nextElem(p)]
    parts = [
        *[format(v, ".17g") for v in a], e1,
        *[format(v, ".17g") for v in b], e2,
        *[format(v, ".17g") for v in c0],
        e3, e4, e5, e6, e7, e8,
        format(onev, ".17g"), e9,
        *[format(v, ".17g") for v in ind],
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
