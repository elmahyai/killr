"""Proof: Python side of withr.tempfiles.with_tempfile, against R's withr::with_tempfile.

Python name: withr.tempfiles.with_tempfile
Observable result: the same values as the R side (with_tempfile-r.R).
One untimed call, then the median of 20 timed calls (time.perf_counter).
Prints one JSON line.
"""
import json
import os
import statistics
import sys
import tempfile
import time
from withr import with_tempfile
import os


def one():
    holder = {}

    def body(p):
        holder["p"] = p
        with open(p, "w") as handle:
            handle.write("abc\n")
        with open(p) as handle:
            return handle.read().splitlines()

    inside = with_tempfile(["p"], body)
    return [inside, 1.0 if os.path.exists(holder["p"]) else 0.0]


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
