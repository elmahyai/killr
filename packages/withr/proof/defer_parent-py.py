"""Proof: Python side of withr.deferred.defer_parent, against R's withr::defer_parent.

Python name: withr.deferred.defer_parent
Observable result: the same values as the R side (defer_parent-r.R).
One untimed call, then the median of 20 timed calls (time.perf_counter).
Prints one JSON line.
"""
import json
import os
import statistics
import sys
import tempfile
import time
from withr import defer, defer_parent, scope


def one():
    bucket = []
    with scope():
        with scope():
            defer_parent(lambda: bucket.append("p"))
            defer(lambda: bucket.append("i"))
        bucket.append("mid")
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
