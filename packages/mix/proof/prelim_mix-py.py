"""Proof: prelim_mix against R mix::prelim.mix (mix 1.0-13), on the fixed inputs of
prelim_mix-r.R. Prints every field of the two results, then the median time in
milliseconds of 20 timed calls.
"""

import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mix.prelim_mix import prelim_mix  # noqa: E402

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


def case_e():
    n = 30
    i = np.arange(1, n + 1)
    c1 = ((i % 4) + 1).astype(float)
    c1[4] = NAN
    x1 = (((i * 7) % 29) - 14) / 8
    x1[1] = NAN
    x1[8] = NAN
    x2 = ((i * i) % 11 - 5) / 4
    return np.column_stack([c1, x1, x2])


FIELDS = ["w", "n", "p", "d", "jmp", "z", "q", "r", "rz", "rw", "nmis", "ro",
          "mdpzgrp", "mdpwgrp", "mobs", "mobsst", "nmobs", "ncells", "ngrp",
          "npattz", "npattw", "npsi", "psi", "xbar", "sdv"]


def num(v):
    arr = np.asarray(v, dtype=float).ravel(order="F")
    return np.where(np.isnan(arr), -999999.0, arr)


def one():
    out = []
    for s in (prelim_mix(case_b(), 2), prelim_mix(case_e(), 1)):
        for f in FIELDS:
            out.append(num(getattr(s, f)))
    return np.concatenate(out)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for v in value:
    print("%.17g" % v)
print("%.17g" % statistics.median(elapsed))
