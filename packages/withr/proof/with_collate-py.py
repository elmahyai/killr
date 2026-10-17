"""Proof: Python side of withr.collate.with_collate, against R's withr::with_collate.

Python name: withr.collate.with_collate
Observable result: the same values as the R side (with_collate-r.R).
One untimed call, then the median of 20 timed calls (time.perf_counter).
Prints one JSON line.
"""
import json
import os
import statistics
import sys
import tempfile
import time
from withr import with_collate
import locale


def one():
    x = ["b\u00e9r\u00e9nice", "boris", "bernard", "b\u00e9atrice"]
    before = locale.setlocale(locale.LC_COLLATE)
    out = with_collate("C", lambda: [x.index(s) + 1 for s in sorted(x, key=locale.strxfrm)])
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
