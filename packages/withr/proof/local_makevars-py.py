"""Proof: Python side of withr.makevars.local_makevars, against R's withr::local_makevars.

Python name: withr.makevars.local_makevars
Observable result: the same values as the R side (local_makevars-r.R).
One untimed call, then the median of 20 timed calls (time.perf_counter).
Prints one JSON line.
"""
import json
import os
import statistics
import sys
import tempfile
import time
from withr import local_makevars, scope
import os


def one():
    fixture = os.path.join(tempfile.gettempdir(), "withr-proof-makevars-local")
    with open(fixture, "w") as handle:
        handle.write("CFLAGS = -O2\nFC = gfortran\n")
    before = os.environ.get("R_MAKEVARS_USER", "unset")

    def f():
        with scope():
            local_makevars({"FC": "gfortran-14"}, path=fixture)
            with open(os.environ["R_MAKEVARS_USER"]) as handle:
                return handle.read().splitlines()

    inside = f()
    return [inside, 1.0 if os.environ.get("R_MAKEVARS_USER", "unset") == before else 0.0]


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
