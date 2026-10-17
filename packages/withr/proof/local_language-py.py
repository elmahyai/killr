"""Proof: Python side of withr.language.local_language, against R's withr::local_language.

Python name: withr.language.local_language
Observable result: the same values as the R side (local_language-r.R).
One untimed call, then the median of 20 timed calls (time.perf_counter).
Prints one JSON line.
"""
import json
import os
import statistics
import sys
import tempfile
import time
from withr import local_language, scope
import os


def one():
    before = os.environ.get("LANGUAGE", "unset")

    def f():
        with scope():
            local_language("de")
            return os.environ.get("LANGUAGE")

    inside = f()
    return [inside, 1.0 if os.environ.get("LANGUAGE", "unset") == before else 0.0]


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
