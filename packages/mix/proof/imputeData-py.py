"""Proof: mix-backed imputeData against R mclust::imputeData (mix 1.0-13).

Runs the same four fixed cases as imputeData-r.R, in the same order, and prints the
imputed values, then the median time in milliseconds of 20 timed calls.
"""

import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mix.imputeData import imputeData  # noqa: E402

NAN = float("nan")


def case_a():
    n = 40
    m = np.zeros((n, 3))
    for i in range(1, n + 1):
        for j in range(1, 4):
            m[i - 1, j - 1] = (((i * (3 * j + 4) + j * j * 7) % 29) - 14) / 8
    for i, j in [(2, 1), (5, 2), (9, 3), (11, 1), (30, 2)]:
        m[i - 1, j - 1] = NAN
    return m


def case_b():
    n = 50
    i = np.arange(1, n + 1)
    c1 = ((i % 3) + 1).astype(float)
    c1[3] = NAN
    c2 = (((i * i) % 2) + 1).astype(float)
    x1 = (((i * 11) % 37) - 18) / 4
    x1[6] = NAN
    x2 = ((((i * i) + 3) % 31) - 15) / 16
    x2[19] = NAN
    return np.column_stack([c1, c2, x1, x2])


def case_c():
    i = np.arange(1, 31)
    x = (((i * 5) % 23) - 11) / 2
    x[2] = NAN
    x[16] = NAN
    return x.reshape(-1, 1)


def case_d():
    i = np.arange(1, 26)
    a = (((i * 3) % 17) - 8) / 4
    b = ((i * i) % 13) / 2
    a[5] = NAN
    b[11] = NAN
    return np.column_stack([a, b])


def num(v):
    arr = np.asarray(v, dtype=float).ravel(order="F")
    return np.where(np.isnan(arr), -999999.0, arr)


def one():
    a = imputeData(case_a(), seed=12345)
    b = imputeData(case_b(), categorical=[True, True, False, False], seed=777)
    c = imputeData(case_c(), seed=2026)
    d = imputeData(case_d(), seed=99)
    return np.concatenate([num(a), num(b), num(c), num(d)])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for v in value:
    print("%.17g" % v)
print("%.17g" % statistics.median(elapsed))
