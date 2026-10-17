"""Proof: ecm_mix against R mix::ecm.mix (mix 1.0-13), on the stlouis data set.

The inputs are the alternative model of ecm_mix-r.R: margins c(1,2,0,2,3,0,1,3), the
design of an intercept, D1, D2, D1*D2 and the linear G effect, and no starting value. One
call is the full ECM fit. The median is over 20 timed calls after one untimed call.
"""

import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mix.ecm_mix import ecm_mix  # noqa: E402
from mix.prelim_mix import prelim_mix  # noqa: E402


def stlouis():
    return np.genfromtxt(Path(__file__).with_name("stlouis.csv"), delimiter=",",
                         skip_header=1)


def num(v):
    arr = np.asarray(v, dtype=float).ravel(order="F")
    return np.where(np.isnan(arr), -999999.0, arr)


s = prelim_mix(stlouis(), 3)
margins = [1, 2, 0, 2, 3, 0, 1, 3]
intercept = np.ones(12)
d1 = np.array([-1, -1, -1, 1, 1, 1, -1, -1, -1, 1, 1, 1], dtype=float)
d2 = np.array([-1, -1, -1, -1, -1, -1, 1, 1, 1, 1, 1, 1], dtype=float)
glin = np.array([-1, 0, 1, -1, 0, 1, -1, 0, 1, -1, 0, 1], dtype=float)
design = np.column_stack([intercept, d1, d2, d1 * d2, glin])


def one():
    th = ecm_mix(s, margins, design, showits=False)
    return np.concatenate([num(th.sigma), num(th.mu), num(th.pi)])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for v in value:
    print("%.17g" % v)
print("%.17g" % statistics.median(elapsed))
