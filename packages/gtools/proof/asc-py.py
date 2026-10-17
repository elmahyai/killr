import json
import statistics
import string
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/gtools")
from gtools.asc import asc


def flat(value):
    if isinstance(value, dict):
        out = []
        for key in value:
            out.extend(flat(value[key]))
        return out
    if isinstance(value, np.ndarray):
        return value.ravel(order="F").astype(float).tolist()
    if isinstance(value, list):
        if not value:
            return []
        if isinstance(value[0], int):
            return [float(item) for item in value]
        out = []
        for item in value:
            out.extend(flat(item))
        return out
    return [float(value)]


def one():
    parts = [
        flat(asc(list(string.ascii_lowercase))),
        flat(asc("hello!")),
        flat(asc(["a", "e", "i", "o", "u", "y"])),
        flat(asc(["ae", "io", "uy"])),
        flat(asc("hello!", simplify=False)),
        flat(asc(["ae", "io", "uy"], simplify=False)),
        flat(asc(["a", "e", "i", "o", "u", "y"], simplify=False)),
        flat(asc(["ae", "io", "uy"], simplify=False)),
        flat(asc("caf\u00e9")),
        flat(asc(["", "a"])),
        flat(asc(["", ""])),
        flat(asc(["a", "hello"])),
        flat(asc([])),
    ]
    return [item for part in parts for item in part]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
