import statistics
import time
from datetime import date, datetime, timezone

import numpy as np

from survival.ratetable_date import RtableDate, ratetableDate


def _fmt(values):
    return "|".join(f"{float(v):.17g}" for v in values)


def _as_numeric(out):
    if isinstance(out, RtableDate):
        return out.values.tolist()
    if isinstance(out, np.ndarray):
        return out.reshape(-1).tolist()
    if isinstance(out, (list, tuple)):
        return [float(v) for v in out]
    return [float(out)]


def serialize(out):
    return _fmt(_as_numeric(out))


def one():
    d = [date(1970, 1, 1), date(1960, 1, 1), date(2000, 6, 15)]
    i = [0, 3653, 14765]
    p = [
        datetime(2000, 6, 15, 23, 59, 59, tzinfo=timezone.utc),
        datetime(1970, 1, 1, 0, 0, 1, tzinfo=timezone.utc),
    ]
    n = [1.5, 2.25]
    return [
        serialize(ratetableDate(d)),
        serialize(ratetableDate(np.asarray(i, dtype=np.int64))),
        serialize(ratetableDate(p)),
        serialize(ratetableDate(n)),
        f"{float(_as_numeric(ratetableDate(42))[0]):.17g}",
    ]


t0 = time.perf_counter()
value = one()
py_untimed = (time.perf_counter() - t0) * 1000

elapsed = []
for _ in range(20):
    t0 = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - t0) * 1000)
py_median = statistics.median(elapsed)

print("\n".join(value))
print("PY_UNTIMED")
print(f"{py_untimed:.17g}")
print("PY_MEDIAN")
print(f"{py_median:.17g}")
