import importlib.util
import json
import statistics
import time

import numpy as np

_ODD_PATH = "/home/ahmed/killr_projects/killr/packages/gtools/gtools/odd.py"
_spec = importlib.util.spec_from_file_location("gtools_odd", _ODD_PATH)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
odd = _mod.odd
_NA_LOGICAL = _mod._NA_LOGICAL


def fmt(v):
    if isinstance(v, (np.integer, int)) and int(v) == int(_NA_LOGICAL):
        return "NA"
    if v is True or v is False or isinstance(v, (bool, np.bool_)):
        return "TRUE" if bool(v) else "FALSE"
    item = np.asarray(v).reshape(()).item()
    if isinstance(item, (np.integer, int)) and int(item) == int(_NA_LOGICAL):
        return "NA"
    return "TRUE" if bool(item) else "FALSE"


def flat(x):
    arr = np.asarray(x, dtype=np.int8).ravel(order="F")
    return [fmt(item) for item in arr]


def one():
    parts = []
    parts.extend(flat(odd(4)))
    parts.extend(flat(odd(np.arange(1, 11, dtype=np.int32))))
    parts.extend(flat(odd(np.arange(1, 11, dtype=np.float64) + 0.5)))
    parts.extend(flat(odd(np.array([-4, -3, -2, -1, 0, 1, 2], dtype=np.float64))))
    parts.extend(flat(odd(np.array([np.inf, -np.inf, np.nan], dtype=np.float64))))
    parts.extend(flat(odd(np.array([np.nan, 1.0, 2.0], dtype=np.float64))))
    parts.extend(flat(odd(np.array([1, 2, 3], dtype=np.int32))))
    parts.extend(
        flat(
            odd(
                np.array([1.5, 2.0, 3.0, 4.0, np.nan, 0.0, -2.0], dtype=np.float64)
            )
        )
    )
    parts.extend(flat(odd(np.array([], dtype=np.int32))))
    parts.extend(flat(odd(np.array([True, False]))))
    return parts


odd(4)
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": "|".join(value), "median_ms": statistics.median(elapsed)}))
