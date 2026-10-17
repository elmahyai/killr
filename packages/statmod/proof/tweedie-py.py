import statistics
import sys
import time
import warnings

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.tweedie import tweedie


def one():
    mus = np.exp(np.linspace(np.log(0.05), np.log(20), 25))
    y = mus * np.concatenate([np.zeros(5), np.full(20, 1.1)])
    wt = np.ones(y.shape)
    f0 = tweedie()
    f15 = tweedie(var_power=1.5, link_power=0)
    f2 = tweedie(var_power=2, link_power=-1)
    f3 = tweedie(var_power=3, link_power=0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fchr = tweedie(var_power="gamma", link_power="log")
    eta0 = f0.linkfun(mus)
    eta15 = f15.linkfun(mus)
    return np.concatenate(
        [
            np.asarray(f0.linkinv(eta0), dtype=float),
            np.asarray(f0.mu_eta(eta0), dtype=float),
            np.asarray(f0.variance(mus), dtype=float),
            np.asarray(f0.dev_resids(y, mus, wt), dtype=float),
            np.array([int(f0.validmu(mus))], dtype=float),
            np.array([int(f0.valideta(eta0))], dtype=float),
            np.asarray(f15.linkinv(eta15), dtype=float),
            np.asarray(f15.mu_eta(eta15), dtype=float),
            np.asarray(f15.variance(mus), dtype=float),
            np.asarray(f15.dev_resids(y, mus, wt), dtype=float),
            np.array([int(f15.validmu(mus))], dtype=float),
            np.asarray(f2.linkfun(mus[:3]), dtype=float),
            np.asarray(f2.dev_resids(y, mus, wt), dtype=float),
            np.asarray(f3.linkfun(mus[:3]), dtype=float),
            np.asarray(fchr.variance(mus[:5]), dtype=float),
            np.asarray(fchr.dev_resids(y, mus, wt), dtype=float),
        ]
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(",".join("%.17g" % float(v) for v in np.asarray(value, dtype=float)))
print("MS")
print("%.17g" % statistics.median(elapsed))
