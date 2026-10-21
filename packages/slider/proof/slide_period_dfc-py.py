import json
import statistics
import time

from datetime import date, timedelta

import polars as pl
from warp import Date

from slider import *


def fmt(value):
    if value is None:
        return "NA"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return format(float(value), ".17e")
    return str(value)


def frame_text(value):
    rows = [
        ":".join(fmt(value[column][row]) for column in value.columns)
        for row in range(value.height)
    ]
    return ",".join(value.columns) + "::" + ";".join(rows)


x = [1, 5, 3, 2, 6, 10]
y = [2, 4, 1, 3, 5, 7]
i = [0, 1, 3, 4, 6, 8]
d = Date([date(2020, 1, 1) + timedelta(days=v) for v in i])


def one():
    return frame_text(slide_period_dfc(x, d, "day", lambda w: {"n": len(w), "s": sum(w)}, before=1))


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
