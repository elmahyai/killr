"""Proof: Python side of withr.rng.local_rng_version, against R's withr::local_rng_version.

Python name: withr.rng.local_rng_version
Observable result: the same values as the R side (local_rng_version-r.R).
One untimed call, then the median of 20 timed calls (time.perf_counter).
Prints one JSON line.
"""
import json
import os
import statistics
import sys
import tempfile
import time
from withr import local_rng_version, scope
from withr._rng import get_kind


def one():
    before = get_kind()

    def f():
        with scope():
            local_rng_version("3.5.0")
            return list(get_kind())

    inside = f()
    return [inside, 1.0 if get_kind() == before else 0.0]


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
