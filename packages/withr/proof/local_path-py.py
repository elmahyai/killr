"""Proof: Python side of withr.path.local_path, against R's withr::local_path.

Python name: withr.path.local_path
Observable result: the same values as the R side (local_path-r.R).
One untimed call, then the median of 20 timed calls (time.perf_counter).
Prints one JSON line.
"""
import json
import os
import statistics
import sys
import tempfile
import time
from withr import local_path, scope
import os


def one():
    before = os.environ.get("PATH", "")

    def f():
        with scope():
            local_path("/usr/sbin", action="suffix")
            return os.environ["PATH"].split(":")

    parts = f()
    return [parts[-1], 1.0 if os.environ.get("PATH", "") == before else 0.0]


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
