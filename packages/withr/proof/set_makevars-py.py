"""Proof: Python side of withr.makevars.set_makevars, against R's withr::set_makevars.

Python name: withr.makevars.set_makevars
Observable result: the same values as the R side (set_makevars-r.R).
One untimed call, then the median of 20 timed calls (time.perf_counter).
Prints one JSON line.
"""
import json
import os
import statistics
import sys
import tempfile
import time
from withr import set_makevars
import os


def one():
    fixture = os.path.join(tempfile.gettempdir(), "withr-proof-set-old")
    new_path = os.path.join(tempfile.gettempdir(), "withr-proof-set-new")
    with open(fixture, "w") as handle:
        handle.write("CFLAGS = -O2\nFC = gfortran\n")
    old = set_makevars({"CFLAGS": "-O3", "LDFLAGS": "-L/opt"}, old_path=fixture, new_path=new_path)
    with open(new_path) as handle:
        written = handle.read().splitlines()
    return [old, written]


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
