import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/MASS")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/boot")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/Formula")

from mass.negative_binomial import negative_binomial


def one():
    fam = negative_binomial(theta=1.75, link="sqrt")
    y = np.array([0, 1, 5, 3, 10], dtype=float)
    mu = np.array([0.5, 1.2, 4.0, 3.0, 8.0], dtype=float)
    wt = np.array([1, 1, 2, 1, 1], dtype=float)
    n = np.ones(len(y))
    dev = float(np.sum(fam.dev_resids(y, mu, wt)))
    eta = fam.linkfun(mu)
    out = []
    out.extend(fam.variance(mu))
    out.extend(fam.dev_resids(y, mu, wt))
    out.append(fam.aic(y, n, mu, wt, dev))
    out.extend(fam.linkfun(mu))
    out.extend(fam.linkinv(eta))
    out.extend(fam.mu_eta(eta))
    out.append(float(fam.validmu(mu)))
    out.append(float(fam.validmu(np.array([1.0, -1.0]))))
    out.append(float(fam.valideta(eta)))
    return out


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for item in value:
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
