"""Proof: Python side of withr.makevars.with_makevars, against R's withr::with_makevars.

Python name: withr.makevars.with_makevars
Observable result: the same values as the R side (with_makevars-r.R).
One untimed call, then the median of 20 timed calls (time.perf_counter).
Prints one JSON line.
"""
import json
import os
import statistics
import sys
import tempfile
import time
from withr import with_makevars
import os


def one():
    fixture = os.path.join(tempfile.gettempdir(), "withr-proof-makevars-with")
    with open(fixture, "w") as handle:
        handle.write("CFLAGS = -O2\nFC = gfortran\n")
    before = os.environ.get("R_MAKEVARS_USER", "unset")
    captured = []

    def body():
        with open(os.environ["R_MAKEVARS_USER"]) as handle:
            captured.append(handle.read().splitlines())

    with_makevars({"CFLAGS": "-O3", "LDFLAGS": "-L/opt"}, body, path=fixture)
    return [captured[0], 1.0 if os.environ.get("R_MAKEVARS_USER", "unset") == before else 0.0]


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
