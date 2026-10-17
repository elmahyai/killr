"""Proof: Python side of withr.envvar.local_envvar, against R's withr::local_envvar.

Python name: withr.envvar.local_envvar
Observable result: the same values as the R side (local_envvar-r.R).
One untimed call, then the median of 20 timed calls (time.perf_counter).
Prints one JSON line.
"""
import json
import os
import statistics
import sys
import tempfile
import time
from withr import local_envvar, scope
import os


def one():
    os.environ.pop("WITHR_PROOF", None)

    def f():
        with scope():
            local_envvar({"WITHR_PROOF": "xyz"})
            return os.environ.get("WITHR_PROOF", "unset")

    inside = f()
    return [inside, os.environ.get("WITHR_PROOF", "unset")]


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
