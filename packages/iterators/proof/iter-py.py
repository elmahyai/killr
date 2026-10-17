import statistics
import sys
import time
import warnings
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from iterators.core import DataFrame, IteratorError, iter, nextElem


def num(value):
    if isinstance(value, np.ndarray):
        values = np.ravel(value, order="F")
        return ",".join(format(item, ".17g") for item in values)
    if isinstance(value, DataFrame):
        flat = []
        for name in value.names:
            flat.extend(value.columns[name])
        return ",".join(format(item, ".17g") for item in flat)
    if isinstance(value, (list, tuple)):
        return ",".join(format(item, ".17g") for item in value)
    return format(value, ".17g")


def err(fn):
    try:
        fn()
        return "OK"
    except IteratorError as exc:
        return exc.message


def one():
    it = iter([1, 2, 3])
    v = [nextElem(it), nextElem(it), nextElem(it)]
    e = err(lambda: nextElem(it))

    it = iter(list(range(1, 7)), checkFunc=lambda i: i % 2 == 0)
    ev = [nextElem(it), nextElem(it), nextElem(it)]

    it = iter([10, 20], recycle=True)
    rc = [nextElem(it), nextElem(it), nextElem(it)]

    it = iter([1.5, 2.5])
    db = [nextElem(it), nextElem(it)]

    it = iter([4, [8, 9]])
    l1 = nextElem(it)
    l2 = nextElem(it)

    it = iter([])
    empty = err(lambda: nextElem(it))

    it = iter([1, 2, 3], checkFunc=lambda i: i < 0)
    none = err(lambda: nextElem(it))

    m = np.arange(1, 7).reshape((2, 3), order="F")
    it = iter(m, by="column", chunksize=2)
    ch1 = nextElem(it)
    ch2 = nextElem(it)
    ch_end = err(lambda: nextElem(it))

    it = iter(m, by="cell")
    cells = [nextElem(it) for _ in range(6)]

    it = iter(m, by="row")
    row1 = nextElem(it)

    it = iter(m, "ce")
    cell1 = nextElem(it)

    it = iter(m, by="column", recycle=True)
    mr = []
    for _ in range(4):
        mr.extend(np.ravel(nextElem(it), order="F").tolist())

    x = np.arange(1, 11).reshape((5, 2), order="F")

    def keep_tenth(chunk):
        return int(np.ravel(chunk, order="F")[4]) % 10 == 0

    it = iter(x, by="column", checkFunc=keep_tenth)
    kept = nextElem(it)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        it = iter(m, by="cell", chunksize=2)
    wtext = "" if not caught else str(caught[0].message).replace("\n", " / ")
    wcell = nextElem(it)

    bad = err(lambda: iter(m, by="c"))
    bad_df = err(lambda: iter(DataFrame({"a": [1, 2]}), by="cell"))

    df = DataFrame({"x": [1, 2, 3], "y": [10, 20, 30]})
    it = iter(df)
    cx = nextElem(it)
    cy = nextElem(it)
    it = iter(df, by="row")
    r1 = nextElem(it)
    r2 = nextElem(it)
    it = iter(df, by="row", recycle=True)
    for _ in range(3):
        nextElem(it)
    rwrap = nextElem(it)

    it = iter(DataFrame({"z": ["a", "b", "c"]}))
    letters = ",".join(nextElem(it))

    def even_row(row):
        return row.columns["x"][0] % 2 == 0

    it = iter(DataFrame({"x": [1, 2, 3, 4]}), by="row", checkFunc=even_row)
    evrow = []
    evrow.extend(nextElem(it).columns["x"])
    evrow.extend(nextElem(it).columns["x"])

    it = iter(DataFrame({"x": [5, 6]}), "row")
    pos = nextElem(it).columns["x"]

    it = iter(lambda i: i * 10)
    f = [nextElem(it), nextElem(it), nextElem(it)]
    it = iter(lambda: 7)
    f0 = [nextElem(it), nextElem(it)]

    def restart(i):
        if i > 2:
            raise IteratorError("StopIteration")
        return i

    it = iter(restart, recycle=True)
    fr = [nextElem(it), nextElem(it), nextElem(it), nextElem(it)]

    def too_high(i):
        if i > 2:
            raise IteratorError("too high")
        return i

    it = iter(too_high)
    fh = [nextElem(it), nextElem(it)]
    fherr = err(lambda: nextElem(it))

    base = iter([9, 8])
    same = "SAME" if iter(base) is base else "DIFF"
    same_v = [nextElem(base), nextElem(base)]

    parts = [
        num(v), e, num(ev), num(rc), num(db), num(l1), num(l2), empty, none,
        num(ch1), num(ch2), ch_end, num(cells), num(row1), num(cell1), num(mr), num(kept),
        wtext, num(wcell), bad, bad_df,
        num(cx), num(cy), num(r1), num(r2), num(rwrap), letters, num(evrow), num(pos),
        num(f), num(f0), num(fr), num(fh), fherr, same, num(same_v),
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
