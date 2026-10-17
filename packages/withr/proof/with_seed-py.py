"""Proof: Python side of withr.seed.with_seed, against R's withr::with_seed.

Python name: withr.seed.with_seed
Observable result: the same values as the R side (with_seed-r.R).
One untimed call, then the median of 20 timed calls (time.perf_counter).
Prints one JSON line.
"""
import json
import os
import statistics
import sys
import tempfile
import time
from withr import with_seed
from withr._rng import runif


def one():
    a = with_seed(1, lambda: runif(5))
    b = with_seed(1, lambda: runif(5), rng_kind="Marsaglia-Multicarry")
    return [a, b]


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
