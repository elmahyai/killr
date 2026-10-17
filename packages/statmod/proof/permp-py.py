import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.permp import permp


def one():
    x = np.arange(6, dtype=float)
    return np.concatenate(
        [
            permp(x=x, nperm=99, n1=6, n2=6),
            permp(x=x, nperm=99, total_nperm=462),
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
