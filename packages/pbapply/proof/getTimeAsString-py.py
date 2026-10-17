import json
import math
import statistics
import time

from pbapply.time import getTimeAsString

TIMES = [
    None,
    0,
    0.4,
    0.5,
    0.6,
    15,
    59.5,
    60,
    65,
    90.5,
    119.5,
    3599,
    3600,
    6005,
    86399,
    86400,
    86401,
    90061,
    1e6,
    1e10,
    2147483647 * 86400,
    2147483647 * 86400 - 1,
    -1,
    -15,
    -59.5,
    -60,
    -61,
    -3600,
    -86400,
    -90061,
    -1e10,
    math.inf,
    -math.inf,
]


def one():
    return [getTimeAsString(value) for value in TIMES]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
