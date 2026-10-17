import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.varfun_digamma import varfun_digamma


def one():
    mus = np.exp(np.linspace(np.log(0.01), np.log(1000), 50))
    return np.concatenate(
        [
            varfun_digamma(mus),
            varfun_digamma(np.array([0.25, 1.5, 7.5, 50, 200], dtype=float)),
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
