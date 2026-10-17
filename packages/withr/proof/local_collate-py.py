"""Proof: Python side of withr.collate.local_collate, against R's withr::local_collate.

Python name: withr.collate.local_collate
Observable result: the same values as the R side (local_collate-r.R).
One untimed call, then the median of 20 timed calls (time.perf_counter).
Prints one JSON line.
"""
import json
import os
import statistics
import sys
import tempfile
import time
from withr import local_collate, scope
import locale


def one():
    x = ["b\u00e9r\u00e9nice", "boris", "bernard", "b\u00e9atrice"]
    before = locale.setlocale(locale.LC_COLLATE)

    def f():
        with scope():
            local_collate("C")
            return [x.index(s) + 1 for s in sorted(x, key=locale.strxfrm)]

    out = f()
    return [out, 1.0 if locale.setlocale(locale.LC_COLLATE) == before else 0.0]


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
