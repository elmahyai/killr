"""Proof: Python side of withr.timezone.local_timezone, against R's withr::local_timezone.

Python name: withr.timezone.local_timezone
Observable result: the same values as the R side (local_timezone-r.R).
One untimed call, then the median of 20 timed calls (time.perf_counter).
Prints one JSON line.
"""
import json
import os
import statistics
import sys
import tempfile
import time
from withr import local_timezone, scope
import time


def one():
    def fmt():
        return time.strftime("%H:%M %Z", time.localtime(0))

    default = fmt()

    def f():
        with scope():
            local_timezone("Asia/Tokyo")
            return fmt()

    inside = f()
    return [inside, 1.0 if fmt() == default else 0.0]


def emit(value, ms):
    items = []
    for piece in value:
        for item in (piece if isinstance(piece, list) else [piece]):
            if isinstance(item, str):
                items.append(json.dumps(item))
            else:
                items.append(repr(float(item)))
    print('{"value": [' + ", ".join(items) + '], "median_ms": ' + repr(float(ms)) + "}")


value = one()
elapsed = []
for _ in range(20):
    t0 = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - t0) * 1000)
emit(value, statistics.median(elapsed))
