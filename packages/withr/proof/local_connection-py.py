"""Proof: Python side of withr.connection.local_connection, against R's withr::local_connection.

Python name: withr.connection.local_connection
Observable result: the same values as the R side (local_connection-r.R).
One untimed call, then the median of 20 timed calls (time.perf_counter).
Prints one JSON line.
"""
import json
import os
import statistics
import sys
import tempfile
import time
from withr import local_connection, scope


def one():
    path = os.path.join(tempfile.gettempdir(), "withr-proof-local-connection-py.txt")

    def f():
        with scope():
            con = local_connection(open(path, "w"))
            con.write("foo\nbar\n")

    f()
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
