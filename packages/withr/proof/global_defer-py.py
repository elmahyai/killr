"""Proof: Python side of withr.deferred.global_defer, against R's withr::global_defer.

Python name: withr.deferred.global_defer
Observable result: the same values as the R side (global_defer-r.R).
One untimed call, then the median of 20 timed calls (time.perf_counter).
Prints one JSON line.
"""
import json
import os
import statistics
import sys
import tempfile
import time
from withr import GLOBAL, deferred_run, global_defer


def one():
    bucket = []
    global_defer(lambda: bucket.append("g1"))
    global_defer(lambda: bucket.append("g2"), priority="last")
    deferred_run(GLOBAL)
    return [bucket]


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
