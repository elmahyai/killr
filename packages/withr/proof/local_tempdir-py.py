"""Proof: Python side of withr.tempfiles.local_tempdir, against R's withr::local_tempdir.

Python name: withr.tempfiles.local_tempdir
Observable result: the same values as the R side (local_tempdir-r.R).
One untimed call, then the median of 20 timed calls (time.perf_counter).
Prints one JSON line.
"""
import json
import os
import statistics
import sys
import tempfile
import time
from withr import local_tempdir, scope
import os


def one():
    holder = {}

    def f():
        with scope():
            d = local_tempdir()
            holder["d"] = d
            return [1.0 if os.path.basename(d).startswith("file") else 0.0,
                    1.0 if os.path.isdir(d) else 0.0]

    inside = f()
    return [inside, 1.0 if os.path.isdir(holder["d"]) else 0.0]


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
