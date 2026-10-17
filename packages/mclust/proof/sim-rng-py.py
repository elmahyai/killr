import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/mclust")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/boot")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/extraDistr")

from boot.rng import set_seed, unif
from extradistr._rng import exp_rand
from mclust._sim_core import r_rnorm, r_sample_prob


def one():
    out = []
    for s in (42, 1, 2024):
        set_seed(s)
        out.extend(r_rnorm(500))
        set_seed(s)
        out.extend(unif() for _ in range(500))
        set_seed(s)
        out.extend(exp_rand() for _ in range(500))
        set_seed(s)
        out.extend(r_sample_prob(3, 300, [0.2, 0.3, 0.5]))
        set_seed(s)
        out.extend(r_sample_prob(3, 300, [1 / 3, 1 / 3, 1 / 3]))
        set_seed(s)
        out.extend(r_sample_prob(5, 200, [0.1, 0.4, 0.1, 0.4, 0.0]))
        set_seed(s)
        r_rnorm(3, 0.0, 0.0)
        out.extend(unif() for _ in range(2))
    return out


value = one()
for v in value:
    print("%.17g" % float(v))
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("%.17g" % statistics.median(elapsed))
