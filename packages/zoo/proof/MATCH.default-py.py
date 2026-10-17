import json
import math
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/zoo")
import datetime as dt

from zoo.match import MATCH_default


def one():
    dates = [dt.date(1970, 1, 1) + dt.timedelta(days=day) for day in (1, 3)]
    times = [
        dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc),
        dt.datetime(1970, 1, 1, 2, tzinfo=dt.timezone.utc),
    ]
    return (
        MATCH_default([0, 1, 5], dates)
        + MATCH_default([0, 3600, 7200], times)
        + MATCH_default([1, 2, 3], [1, 2, 3], incomparables=2)
        + MATCH_default(["b", "a", "c"], ["a", "b"])
    )


def as_text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        if value and isinstance(value[0], str):
            return "|".join(value)
        parts = []
        for item in value:
            if item is None or (isinstance(item, float) and math.isnan(item)):
                parts.append("NA")
            else:
                parts.append(format(float(item), ".16g"))
        return "|".join(parts)
    array = np.asarray(value, dtype=float).reshape(-1)
    parts = []
    for number in array:
        number = float(number)
        parts.append("NA" if math.isnan(number) else format(number, ".16g"))
    return "|".join(parts)


value = as_text(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
