import json
import math
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/zoo")

from zoo.match import MATCH_times
from zoo.times import Times, times


def c_times(*parts):
    values = []
    for part in parts:
        if part is None:
            values.append(float("nan"))
        elif isinstance(part, Times):
            values.extend(part._values.tolist())
        else:
            values.append(float(part))
    return Times(values)


def one():
    return (
        MATCH_times(
            c_times(
                times(["12:34:56.5", "12:34:57.4", "12:35:00"]),
                None,
                times("00:00:01"),
            ),
            c_times(
                times(["12:34:56", "12:35:00", "00:00:01"]),
                None,
            ),
            nomatch=0,
        )
        + MATCH_times(
            c_times(times(["12:34:56.5", "12:34:57.4"])),
            c_times(times(["12:34:56", "12:35:00"])),
            units="min",
        )
    )


def as_text(value):
    if isinstance(value, (list, tuple)):
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
