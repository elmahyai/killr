"""Proof: getparam_mix against R mix::getparam.mix (mix 1.0-13), on the stlouis data set.

The inputs are the setup of getparam_mix-r.R: the unrestricted EM estimate from the
translated em_mix. One call is getparam with corr = FALSE and then with corr = TRUE. The
median is over 20 timed calls after one untimed call.
"""

import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mix.em_mix import em_mix  # noqa: E402
from mix.getparam_mix import getparam_mix  # noqa: E402
from mix.prelim_mix import prelim_mix  # noqa: E402


def stlouis():
    return np.genfromtxt(Path(__file__).with_name("stlouis.csv"), delimiter=",",
                         skip_header=1)


def num(v):
    arr = np.asarray(v, dtype=float).ravel(order="F")
    return np.where(np.isnan(arr), -999999.0, arr)


s = prelim_mix(stlouis(), 3)
th_em = em_mix(s, showits=False)


def one():
    a = getparam_mix(s, th_em)
    b = getparam_mix(s, th_em, corr=True)
    return np.concatenate([num(a["pi"]), num(a["mu"]), num(a["sigma"]), num(b["pi"]),
                           num(b["mu"]), num(b["sdv"]), num(b["r"])])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for v in value:
    print("%.17g" % v)
print("%.17g" % statistics.median(elapsed))
