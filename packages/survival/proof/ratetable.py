import statistics
import time
from datetime import date

import numpy as np

from survival.fromtimeline import Categorical
from survival.ratetable import ratetable


def serialize_ratetable(rt):
    flat = rt.values.reshape(-1, order="F")
    tokens = [f"{v:.17g}" for v in flat]
    isd = ",".join("1" if flag else "0" for flag in rt.is_date)
    lev_parts = []
    for item in rt.levlist:
        if item is None:
            lev_parts.append("NULL")
        else:
            lev_parts.append(";".join(item))
    return [
        ",".join(tokens),
        isd,
        "|".join(lev_parts),
        ",".join(rt.colnames),
    ]


def one():
    d = [date(1970, 1, 1), date(1960, 1, 1), date(2000, 6, 15)]
    rt = ratetable(
        age=[50.0, 60.0, 70.0],
        sex=Categorical(["M", "F", "M"], ["M", "F"]),
        birth=d,
        wt=1.5,
        entry=np.array([0, 3653, 14765], dtype=np.int64),
    )
    return serialize_ratetable(rt)


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
