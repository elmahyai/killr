import json
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/gtools")
from gtools.na_replace import NA, _NA_INT, _NA_LOGICAL, _NA_REAL
from gtools.stat_mode import stat_mode


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
    if isinstance(v, (list, tuple)):
        if len(v) == 0:
            return ""
        return ";".join(fmt(item) for item in v)
    if isinstance(v, np.ndarray):
        if v.size == 0:
            return ""
        if v.size == 1:
            return fmt(v.reshape(()).item())
        return ";".join(fmt(item) for item in v.ravel(order="F"))
    if isinstance(v, (bool, np.bool_)):
        return "TRUE" if bool(v) else "FALSE"
    if isinstance(v, str):
        return json_str(v)
    if isinstance(v, (complex, np.complexfloating)):
        re = float(np.real(v))
        im = float(np.imag(v))
        if np.isnan(re) or np.isnan(im):
            return "NA"
        return f"{re:.16g}+{im:.16g}i"
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
    return format(v)


def flat(x):
    return fmt(x)


def one():
    chr_vec = ["a", "d", "d", "h", "h", NA, NA]
    num_vec = np.array([2.0, 3.0, 3.0, 4.0, 4.0, _NA_REAL, _NA_REAL], dtype=np.float64)
    tie_num = np.array([1.0, 1.0, 2.0, 2.0], dtype=np.float64)
    parts = [
        flat(stat_mode(chr_vec)),
        flat(stat_mode(chr_vec, na_rm=False)),
        flat(stat_mode(chr_vec, na_rm=False, ties="first")),
        flat(stat_mode(chr_vec, na_rm=False, ties="last")),
        flat(stat_mode(num_vec)),
        flat(stat_mode(num_vec, na_rm=False)),
        flat(stat_mode(num_vec, na_rm=False, ties="first")),
        flat(stat_mode(num_vec, na_rm=False, ties="last")),
        flat(stat_mode(tie_num, ties="missing")),
        flat(stat_mode(tie_num, ties="first")),
        flat(stat_mode(tie_num, ties="last")),
        flat(stat_mode(tie_num, ties="all")),
        flat(stat_mode([True, True])),
        flat(stat_mode([False, False, True, True])),
        flat(stat_mode(np.array([_NA_REAL], dtype=np.float64))),
        flat(stat_mode(2)),
        flat(stat_mode(NA)),
        flat(stat_mode("a")),
        flat(stat_mode(np.array([_NA_REAL, _NA_REAL, _NA_REAL], dtype=np.float64))),
        flat(stat_mode(np.array([], dtype=np.float64))),
        flat(stat_mode(np.array([], dtype=np.complex128))),
        flat(stat_mode(np.array([], dtype=np.int32))),
        flat(stat_mode([])),
        flat(stat_mode(np.array([1, 2, 2], dtype=np.int32))),
        flat(stat_mode(np.array([1 + 1j, 2 + 2j, 2 + 2j], dtype=np.complex128))),
    ]
    return parts


stat_mode(np.array([2.0], dtype=np.float64))
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": "|".join(value), "median_ms": statistics.median(elapsed)}))
