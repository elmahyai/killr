import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.digamma import Digamma


def one():
    f = Digamma()
    f2 = Digamma(link=2)
    mus = np.exp(np.linspace(np.log(0.05), np.log(50), 40))
    y = mus * 1.1
    eta = f.linkfun(mus)
    return np.concatenate(
        [
            np.asarray(f.linkinv(eta), dtype=float),
            np.asarray(f.mu_eta(eta), dtype=float),
            np.asarray(f.variance(mus), dtype=float),
            np.asarray(f.dev_resids(y, mus, 1), dtype=float),
            np.array([int(f.validmu(mus))], dtype=float),
            np.array([int(f.valideta(eta))], dtype=float),
            np.asarray(f2.linkfun(mus[:3]), dtype=float),
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
