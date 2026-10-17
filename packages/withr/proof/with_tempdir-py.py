"""Proof: Python side of withr.tempfiles.with_tempdir, against R's withr::with_tempdir.

Python name: withr.tempfiles.with_tempdir
Observable result: the same values as the R side (with_tempdir-r.R).
One untimed call, then the median of 20 timed calls (time.perf_counter).
Prints one JSON line.
"""
import json
import os
import statistics
import sys
import tempfile
import time
from withr import with_tempdir
import os


def one():
    before = os.getcwd()
    holder = {}

    def body():
        here = os.getcwd()
        holder["dir"] = here
        return [1.0 if os.path.basename(here).startswith("file") else 0.0,
                1.0 if os.path.isdir(here) else 0.0]

    inside = with_tempdir(body)
    return [inside, 1.0 if os.getcwd() == before else 0.0,
            1.0 if os.path.isdir(holder["dir"]) else 0.0]


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
