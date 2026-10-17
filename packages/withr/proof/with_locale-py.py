"""Proof: Python side of withr.locale_settings.with_locale, against R's withr::with_locale.

Python name: withr.locale_settings.with_locale
Observable result: the same values as the R side (with_locale-r.R).
One untimed call, then the median of 20 timed calls (time.perf_counter).
Prints one JSON line.
"""
import json
import os
import statistics
import sys
import tempfile
import time
from withr import with_locale
import locale


def one():
    before = locale.setlocale(locale.LC_COLLATE)
    inside = with_locale({"LC_COLLATE": "C"}, lambda: locale.setlocale(locale.LC_COLLATE))
    return [inside, 1.0 if locale.setlocale(locale.LC_COLLATE) == before else 0.0]


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
