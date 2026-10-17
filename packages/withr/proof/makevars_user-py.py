"""Proof: Python side of withr.makevars.makevars_user, against R's withr::makevars_user.

Python name: withr.makevars.makevars_user
Observable result: the same values as the R side (makevars_user-r.R).
One untimed call, then the median of 20 timed calls (time.perf_counter).
Prints one JSON line.
"""
import json
import os
import statistics
import sys
import tempfile
import time
from withr import makevars_user, with_envvar
import os


def one():
    fixture = os.path.join(tempfile.gettempdir(), "Makevars-user-proof")
    with open(fixture, "w") as handle:
        handle.write("CFLAGS = -O2\n")
    found = with_envvar({"R_MAKEVARS_USER": fixture},
                        lambda: [os.path.basename(p) for p in makevars_user()])
    count = with_envvar({"R_MAKEVARS_USER": fixture}, lambda: len(makevars_user()))
    return [found, count]


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
