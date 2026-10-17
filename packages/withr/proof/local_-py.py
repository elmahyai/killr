"""Proof: Python side of withr.factory.local_, against R's withr::local_.

Python name: withr.factory.local_
Observable result: the same values as the R side (local_-r.R).
One untimed call, then the median of 20 timed calls (time.perf_counter).
Prints one JSON line.
"""
import json
import os
import statistics
import sys
import tempfile
import time
from withr import local_, scope

state = {"x": 0}


def setx(new):
    old = state["x"]
    state["x"] = new
    return old


def resetx(old):
    state["x"] = old

local_x = local_(setx, resetx)



def one():
    state["x"] = 0

    def f():
        with scope():
            old = local_x(5)
            return [old, state["x"]]

    inside = f()
    return [inside, state["x"]]


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
