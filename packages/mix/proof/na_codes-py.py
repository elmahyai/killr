"""Proof: na_to_snglcode, na_to_icode and code_to_na against the R helpers
.na.to.snglcode, .na.to.icode and .code.to.na of mix 1.0-13 (na_codes-r.R).
"""

import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mix.na_codes import code_to_na, na_to_icode, na_to_snglcode  # noqa: E402

NAN = float("nan")

x = np.array([1.5, NAN, -2.25, 999, NAN, 0.125, 7, 999, NAN, -0.5])
# R: matrix(c(1, NA, 3, 2, 999, NA, 1, 2, 3, NA), 5), filled by column
m = np.column_stack([[1, NAN, 3, 2, 999], [NAN, 1, 2, 3, NAN]])


def num(v):
    arr = np.asarray(v, dtype=float).ravel(order="F")
    return np.where(np.isnan(arr), -999999.0, arr)


def one():
    return np.concatenate([
        num(na_to_snglcode(x, 999)), num(na_to_icode(x, 1)), num(code_to_na(x, 999)),
        num(na_to_snglcode(m, 0)), num(na_to_icode(m, 9)), num(code_to_na(m, 999)),
    ])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for v in value:
    print("%.17g" % v)
print("%.17g" % statistics.median(elapsed))
