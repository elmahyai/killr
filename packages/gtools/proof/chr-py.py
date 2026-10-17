import json
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/gtools")
from gtools.asc import asc
from gtools.chr import chr
from gtools.na_replace import _NA_INT


def flat(value):
    if isinstance(value, dict):
        out = []
        for key in value:
            out.extend(flat(value[key]))
        return out
    if isinstance(value, list):
        if not value:
            return []
        return [item for part in value for item in flat(part)]
    if isinstance(value, np.ndarray):
        if value.size == 0:
            return []
        if value.dtype == object:
            out = []
            for item in value.ravel(order="C"):
                out.extend(flat(str(item)))
            return out
        return value.ravel(order="F").astype(float).tolist()
    text = "" if value is None else str(value)
    if not text:
        return []
    return list(text.encode("latin-1"))


def one():
    parts = [
        flat(chr(np.arange(65, 91, dtype=np.int64))),
        flat(chr(asc("hello!"))),
        flat(chr(asc("hello!", simplify=False))),
        flat(chr(asc(["ae", "io", "uy"]))),
        flat(chr(asc(["a", "e", "i", "o", "u", "y"], simplify=False))),
        flat(chr(asc(["ae", "io", "uy"], simplify=False))),
        flat(chr([104, 101, 108, 108, 111, 33])),
        flat(chr(65)),
        flat(chr([int(_NA_INT), 65])),
        flat(chr(np.array([], dtype=np.int64))),
        flat(chr([[104, 101], 65])),
        flat(chr([256, -1])),
        flat(chr(asc(["a", "hello"]))),
    ]
    return [item for part in parts for item in part]


chr(65)
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
