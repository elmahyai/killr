"""Proof: Python side of withr.options.local_options, against R's withr::local_options.

Python name: withr.options.local_options
Observable result: the same values as the R side (local_options-r.R).
One untimed call, then the median of 20 timed calls (time.perf_counter).
Prints one JSON line.
"""
import json
import os
import statistics
import sys
import tempfile
import time
from withr import local_options, scope
from withr.options import get_option


def one():
    def f():
        with scope():
            local_options({"digits": 4})
            return get_option("digits")

    inside = f()
    return [inside, get_option("digits")]


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
