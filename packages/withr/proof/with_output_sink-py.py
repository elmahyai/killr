"""Proof: Python side of withr.sink.with_output_sink, against R's withr::with_output_sink.

Python name: withr.sink.with_output_sink
Observable result: the same values as the R side (with_output_sink-r.R).
One untimed call, then the median of 20 timed calls (time.perf_counter).
Prints one JSON line.
"""
import json
import os
import statistics
import sys
import tempfile
import time
from withr import with_output_sink
import os


def one():
    path = os.path.join(tempfile.gettempdir(), "withr-proof-output-py.txt")
    with_output_sink(path, lambda: print("hello"))
    with open(path) as handle:
        return [handle.read().splitlines()]


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
