"""Proof: Python side of withr.envvar.with_envvar, against R's withr::with_envvar.

Python name: withr.envvar.with_envvar
Observable result: the same values as the R side (with_envvar-r.R).
One untimed call, then the median of 20 timed calls (time.perf_counter).
Prints one JSON line.
"""
import json
import os
import statistics
import sys
import tempfile
import time
from withr import with_envvar
import os


def one():
    os.environ["WITHR_PROOF"] = "1"
    suffixed = with_envvar({"WITHR_PROOF": "2"}, lambda: os.environ.get("WITHR_PROOF", "unset"),
                           action="suffix")
    restored = os.environ.get("WITHR_PROOF", "unset")
    os.environ.pop("WITHR_PROOF", None)
    return [suffixed, restored]


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
