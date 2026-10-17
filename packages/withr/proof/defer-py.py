"""Proof: Python side of withr.deferred.defer, against R's withr::defer.

Python name: withr.deferred.defer
Observable result: the same values as the R side (defer-r.R).
One untimed call, then the median of 20 timed calls (time.perf_counter).
Prints one JSON line.
"""
import json
import os
import statistics
import sys
import tempfile
import time
from withr import defer, scope


def one():
    bucket = []
    with scope():
        defer(lambda: bucket.append("a"))
        defer(lambda: bucket.append("b"))
        defer(lambda: bucket.append("c"), priority="last")
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
