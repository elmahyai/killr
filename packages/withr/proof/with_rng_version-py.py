"""Proof: Python side of withr.rng.with_rng_version, against R's withr::with_rng_version.

Python name: withr.rng.with_rng_version
Observable result: the same values as the R side (with_rng_version-r.R).
One untimed call, then the median of 20 timed calls (time.perf_counter).
Prints one JSON line.
"""
import json
import os
import statistics
import sys
import tempfile
import time
from withr import with_rng_version, with_seed
from withr._rng import get_kind, runif


def one():
    before = get_kind()
    inside = with_rng_version("3.5.0", lambda: list(get_kind()))
    inside2 = with_rng_version("1.6.0", lambda: list(get_kind()))
    stream = with_rng_version("1.6.0", lambda: with_seed(1, lambda: runif(3)))
    restored = 1.0 if get_kind() == before else 0.0
    return [inside, inside2, stream, restored]


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
