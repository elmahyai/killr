"""Proof: loglik_mix against R mix::loglik.mix (mix 1.0-13), on the stlouis data set.

The inputs are the setup of loglik_mix-r.R: the unrestricted EM estimate and the ECM
estimate of the alternative model, both from the translated em_mix and ecm_mix. One call
is the two log-likelihoods. The median is over 20 timed calls after one untimed call.
"""

import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mix.ecm_mix import ecm_mix  # noqa: E402
from mix.em_mix import em_mix  # noqa: E402
from mix.loglik_mix import loglik_mix  # noqa: E402
from mix.prelim_mix import prelim_mix  # noqa: E402


def stlouis():
    return np.genfromtxt(Path(__file__).with_name("stlouis.csv"), delimiter=",",
                         skip_header=1)


def num(v):
    arr = np.asarray(v, dtype=float).ravel(order="F")
    return np.where(np.isnan(arr), -999999.0, arr)


s = prelim_mix(stlouis(), 3)
th_em = em_mix(s, showits=False)
margins = [1, 2, 0, 2, 3, 0, 1, 3]
intercept = np.ones(12)
d1 = np.array([-1, -1, -1, 1, 1, 1, -1, -1, -1, 1, 1, 1], dtype=float)
d2 = np.array([-1, -1, -1, -1, -1, -1, 1, 1, 1, 1, 1, 1], dtype=float)
glin = np.array([-1, 0, 1, -1, 0, 1, -1, 0, 1, -1, 0, 1], dtype=float)
design = np.column_stack([intercept, d1, d2, d1 * d2, glin])
th_ecm = ecm_mix(s, margins, design, showits=False)


def one():
    return np.concatenate([num([loglik_mix(s, th_em)]),
                           num([loglik_mix(s, th_ecm)])])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for v in value:
    print("%.17g" % v)
print("%.17g" % statistics.median(elapsed))
