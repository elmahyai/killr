import json
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/abind")
from abind.abind import Array
from abind.afill_replacement import afill_replacement


def one():
    out = []

    x = Array(
        np.zeros((4, 3), order="F"),
        dimnames=[list("abcd"), list("XYZ")],
    )
    y = Array(
        np.arange(1, 5, dtype=float).reshape((2, 2), order="F"),
        dimnames=[list("bc"), list("YZ")],
    )
    afill_replacement(x, value=y)
    out.extend(float(v) for v in np.ravel(x.data, order="F"))

    x3 = Array(
        np.zeros((2, 4, 3), order="F"),
        dimnames=[list("AB"), list("abcd"), list("XYZ")],
    )
    y3 = Array(
        np.arange(1, 5, dtype=float).reshape((2, 2), order="F"),
        dimnames=[list("bc"), list("YZ")],
    )
    afill_replacement(x3, 1, None, None, value=y3)
    out.extend(float(v) for v in np.ravel(x3.data, order="F"))

    x4 = Array(
        np.zeros((2, 4, 3), order="F"),
        dimnames=[list("AB"), list("abcd"), list("XYZ")],
    )
    afill_replacement(x4, True, None, None, value=y3)
    out.extend(float(v) for v in np.ravel(x4.data, order="F"))

    x5 = Array(
        np.zeros((2, 3, 4), order="F"),
        dimnames=[list("ab"), list("ABC"), list("wxyz")],
    )
    y5 = Array(
        np.arange(1, 7, dtype=float).reshape((2, 3), order="F"),
        dimnames=[list("AB"), list("wxy")],
    )
    afill_replacement(x5, True, None, None, value=y5)
    out.extend(float(v) for v in np.ravel(x5.data, order="F"))

    x6 = Array(
        np.arange(1, 25, dtype=float).reshape((6, 4), order="F"),
        dimnames=[list("ABCDEF"), list("wxyz")],
    )
    y6 = Array(
        -np.arange(1, 7, dtype=float).reshape((3, 2), order="F"),
        dimnames=[list("BCD"), list("xy")],
    )
    afill_replacement(x6, value=y6)
    out.extend(float(v) for v in np.ravel(x6.data, order="F"))

    x7 = Array(
        np.arange(1, 25, dtype=float).reshape((6, 4), order="F"),
        dimnames=[list("ABCDEF"), list("wxyz")],
    )
    y7 = Array(
        -np.arange(1, 7, dtype=float).reshape((3, 2), order="F"),
        dimnames=[list("EFG"), list("xy")],
    )
    afill_replacement(x7, excess_ok=True, value=y7)
    out.extend(float(v) for v in np.ravel(x7.data, order="F"))

    xv = Array(np.zeros(4), names=list("ABCD"))
    afill_replacement(xv, value=Array(np.array([1.0, 2.0]), names=list("BC")))
    out.extend(float(v) for v in np.ravel(xv.data, order="F"))

    return out


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
