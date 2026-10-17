"""Proof: Python side of withr.directory.with_dir, against R's withr::with_dir.

Python name: withr.directory.with_dir
Observable result: the same values as the R side (with_dir-r.R).
One untimed call, then the median of 20 timed calls (time.perf_counter).
Prints one JSON line.
"""
import json
import os
import statistics
import sys
import tempfile
import time
from withr import with_dir
import os


def one():
    start = os.getcwd()
    inside = with_dir("/usr", lambda: os.getcwd())
    return [inside, 1.0 if os.getcwd() == start else 0.0]


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
