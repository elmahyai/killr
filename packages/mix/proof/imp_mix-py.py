"""Proof: imp_mix against R mix::imp.mix (mix 1.0-13), on the fixed inputs of
imp_mix-r.R. Two imputations, each after reseeding with 777.
"""

import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mix.da_mix import da_mix  # noqa: E402
from mix.em_mix import em_mix  # noqa: E402
from mix.imp_mix import imp_mix  # noqa: E402
from mix.prelim_mix import prelim_mix  # noqa: E402
from mix.rngseed import rngseed  # noqa: E402

NAN = float("nan")


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


def num(v):
    arr = np.asarray(v, dtype=float).ravel(order="F")
    return np.where(np.isnan(arr), -999999.0, arr)


def one():
    s = prelim_mix(case_b(), 2)
    th = em_mix(s, showits=False)
    rngseed(777)
    newtheta = da_mix(s, th, steps=100, showits=False)
    rngseed(777)
    x1 = imp_mix(s, newtheta)
    rngseed(777)
    x2 = imp_mix(s, newtheta)
    return np.concatenate([num(x1), num(x2)])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for v in value:
    print("%.17g" % v)
print("%.17g" % statistics.median(elapsed))
