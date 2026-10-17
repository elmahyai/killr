"""Proof: Python side of withr.seed.with_preserve_seed, against R's withr::with_preserve_seed.

Python name: withr.seed.with_preserve_seed
Observable result: the same values as the R side (with_preserve_seed-r.R).
One untimed call, then the median of 20 timed calls (time.perf_counter).
Prints one JSON line.
"""
import json
import os
import statistics
import sys
import tempfile
import time
from withr import with_preserve_seed
from withr._rng import runif, set_seed


def one():
    set_seed(2)
    a = with_preserve_seed(lambda: runif(3))
    b = runif(3)
    return [a + b]


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
