import json
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/gtools")
from gtools.na_replace import NA, _NA_INT, _NA_LOGICAL, _NA_REAL, na_replace


def json_str(text):
    parts = []
    for char in text:
        cp = ord(char)
        if cp == 34:
            parts.append('\\"')
        elif cp == 92:
            parts.append("\\\\")
        elif cp == 10:
            parts.append("\\n")
        elif cp == 13:
            parts.append("\\r")
        elif cp == 9:
            parts.append("\\t")
        elif cp < 32 or cp == 127:
            parts.append(f"\\u{cp:04x}")
        else:
            parts.append(char)
    return '"' + "".join(parts) + '"'


def fmt(v):
    if v is NA:
        return "NA"
    if isinstance(v, complex) or (isinstance(v, np.complexfloating)):
        re = float(np.real(v))
        im = float(np.imag(v))
        if np.isnan(re) or np.isnan(im):
            return "NA"
        return f"{re:.16g}+{im:.16g}i"
    if isinstance(v, (bool, np.bool_)):
        return "TRUE" if v else "FALSE"
    if isinstance(v, str):
        return json_str(v)
    if isinstance(v, (np.integer, int)) and not isinstance(v, bool):
        if np.int32(v) == _NA_INT:
            return "NA"
        return format(float(v), ".16g")
    if isinstance(v, (np.floating, float)):
        if np.isnan(v):
            return "NA"
        return format(float(v), ".16g")
    if isinstance(v, np.int8):
        code = int(v)
        if code == int(_NA_LOGICAL):
            return "NA"
        return "TRUE" if code == 1 else "FALSE"
    item = np.asarray(v).reshape(()).item()
    return fmt(item)


def flat(x):
    if isinstance(x, np.ndarray):
        if x.ndim == 2:
            items = x.reshape(-1, order="F")
        else:
            items = x.ravel(order="F")
        return [fmt(item) for item in items]
    if isinstance(x, list):
        return [fmt(item) for item in x]
    return [fmt(x)]


def r_median(x, na_rm=False):
    arr = np.asarray(x, dtype=np.float64)
    if na_rm:
        arr = arr[~np.isnan(arr)]
    return float(np.median(arr))


def one():
    x = np.array([1.0, 2.0, 3.0, _NA_REAL, 6.0, 7.0, 8.0, _NA_REAL, _NA_REAL])
    parts = []
    parts.extend(flat(na_replace(x, 999)))
    parts.extend(flat(na_replace(x, r_median, na_rm=True)))
    parts.extend(flat(na_replace(np.array([1, 2, _NA_INT, 4], dtype=np.int32), np.int32(0))))
    parts.extend(flat(na_replace([True, NA, False], False)))
    parts.extend(flat(na_replace([ "a", NA, "c"], "999")))
    parts.extend(flat(na_replace(np.array([[1.0, 3.0], [_NA_REAL, 4.0]]), 0)))
    cx = np.array([1 + 1j, 0 + 0j], dtype=np.complex128)
    cx[1] = complex(np.nan, 0.0)
    parts.extend(flat(na_replace(cx, 0)))
    nan_x = np.array([1.0, float("nan"), 3.0])
    parts.extend(flat(na_replace(nan_x, 0)))
    return parts


na_replace(np.array([1.0, 2.0]), 0)
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": "|".join(value), "median_ms": statistics.median(elapsed)}))
