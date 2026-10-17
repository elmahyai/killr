import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from iterators.core import IteratorError, icount, iter, nextElem


def flat(value):
    if isinstance(value, np.ndarray):
        return [format(item, ".17g") for item in np.ravel(value, order="F")]
    return [format(value, ".17g")]


def one():
    it = iter(["a", "b", "c"])
    ch = [nextElem(it), nextElem(it), nextElem(it)]
    try:
        nextElem(it)
        e = "OK"
    except IteratorError as exc:
        e = exc.message
    it = iter([4, 5, 6])
    n = [nextElem(it), nextElem(it), nextElem(it)]
    it = icount(2)
    k = [nextElem(it), nextElem(it)]
    try:
        nextElem(it)
        ek = "OK"
    except IteratorError as exc:
        ek = exc.message
    m = np.arange(1, 7).reshape((2, 3), order="F")
    it = iter(m, by="column", chunksize=2)
    p1 = flat(nextElem(it))
    p2 = flat(nextElem(it))
    it = iter(lambda i: i * 10)
    f = [nextElem(it), nextElem(it)]
    it = iter([1, 2, 3, 4, 5], checkFunc=lambda i: i != 3)
    sk = [nextElem(it), nextElem(it), nextElem(it), nextElem(it)]
    parts = [
        *ch, e,
        *[format(v, ".17g") for v in n],
        *[format(v, ".17g") for v in k], ek,
        *p1, *p2,
        *[format(v, ".17g") for v in f],
        *[format(v, ".17g") for v in sk],
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
