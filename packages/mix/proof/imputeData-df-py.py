"""Proof: imputeData on a numeric array and on data frames, against R mclust::imputeData (mix 1.0-13).

Runs the same five cases as imputeData-df-r.R, in the same order, and prints one header per
case ("# name nrow ncol categorical-columns") followed by the imputed values in column-major
order (NA as "NA"). Then the median time in milliseconds of 20 timed calls of the whole set.
"""

import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mix.imputeData import Factor, imputeData  # noqa: E402

NAN = float("nan")


def array_a():
    n = 40
    m = np.zeros((n, 3))
    for i in range(1, n + 1):
        for j in range(1, 4):
            m[i - 1, j - 1] = (((i * (3 * j + 4) + j * j * 7) % 29) - 14) / 8
    for i, j in [(2, 1), (5, 2), (9, 3), (11, 1), (30, 2)]:
        m[i - 1, j - 1] = NAN
    return m


def array_c():
    i = np.arange(1, 31)
    x = (((i * 5) % 23) - 11) / 2
    x[2] = NAN
    x[16] = NAN
    return x.reshape(-1, 1)


def frame_mixed():
    n = 36
    i = np.arange(1, n + 1)
    c1 = Factor([str(v) for v in (i % 3) + 1])
    c2 = Factor([str(v) for v in ((i * i) % 2) + 1])
    x1 = (((i * 11) % 37) - 18) / 7
    x1[6] = NAN
    x2 = (((i * i + 3) % 31) - 15) / 3
    x2[19] = NAN
    scales = np.array([1e-9, 1.0, 1e6, 1e-3])
    x3 = (((i * 5) % 13) - 6) / 7 * scales[i % 4]
    x3[11] = NAN
    return {"c1": c1, "x1": x1, "c2": c2, "x2": x2, "x3": x3}


def frame_numeric():
    i = np.arange(1, 26)
    a = (((i * 3) % 17) - 8) / 7
    b = ((i * i) % 13) / 3
    a[5] = NAN
    b[11] = NAN
    return {"a": a, "b": b}


def cells(name, out, cat_cols):
    out = np.asarray(out, dtype=float)
    if out.ndim == 1:
        out = out.reshape(-1, 1)
    lines = ["# %s %d %d %s" % (name, out.shape[0], out.shape[1], ",".join(str(c) for c in cat_cols))]
    for v in out.ravel(order="F"):
        lines.append("NA" if np.isnan(v) else "%.17g" % v)
    return lines


def run_all():
    lines = []
    lines += cells("array_a", imputeData(array_a(), seed=12345), [])
    lines += cells("array_c", imputeData(array_c(), seed=2026), [])
    lines += cells("frame_null", imputeData(frame_mixed(), seed=4242), [])
    lines += cells(
        "frame_categorical",
        imputeData(frame_mixed(), categorical=[True, False, True, False, False], seed=4242),
        [1, 3],
    )
    lines += cells("frame_numeric", imputeData(frame_numeric(), seed=99), [])
    return lines


value = run_all()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    run_all()
    elapsed.append((time.perf_counter() - started) * 1000)
for line in value:
    print(line)
print("%.17g" % statistics.median(elapsed))
