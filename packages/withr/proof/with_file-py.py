"""Proof: Python side of withr.files.with_file, against R's withr::with_file.

Python name: withr.files.with_file
Observable result: the same values as the R side (with_file-r.R).
One untimed call, then the median of 20 timed calls (time.perf_counter).
Prints one JSON line.
"""
import json
import os
import statistics
import sys
import tempfile
import time
from withr import with_file
import os


def one():
    path = os.path.join(tempfile.gettempdir(), "withr-proof-with-file-py.txt")
    captured = []

    def body():
        with open(path, "w") as handle:
            handle.write("foo\n")
        with open(path) as handle:
            captured.append(handle.read().splitlines())

    with_file([path], body)
    return [captured[0], 1.0 if os.path.exists(path) else 0.0]


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
