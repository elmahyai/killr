"""Proof: Python side of withr.seed.local_seed, against R's withr::local_seed.

Python name: withr.seed.local_seed
Observable result: the same values as the R side (local_seed-r.R).
One untimed call, then the median of 20 timed calls (time.perf_counter).
Prints one JSON line.
"""
import json
import os
import statistics
import sys
import tempfile
import time
from withr import local_seed, scope
from withr._rng import runif, set_seed


def one():
    set_seed(5)

    def f():
        with scope():
            local_seed(1)
            return runif(2)

    a = f()
    b = runif(1)
    set_seed(5)
    expected = runif(1)
    return [a, b, expected]


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
