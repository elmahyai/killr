import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/MASS")

from mass.fitdistr import fitdistr

_X = np.array(
    [float(line) for line in Path(__file__).with_name("fitdistr-x.txt").read_text().splitlines()],
    dtype=float,
)


def one():
    fit = fitdistr(_X, "normal")
    vc = fit.vcov
    return np.array(
        [
            fit.estimate[0],
            fit.estimate[1],
            fit.sd[0],
            fit.sd[1],
            fit.loglik,
            vc[0, 0],
            vc[1, 0],
            vc[0, 1],
            vc[1, 1],
            fit.n,
        ],
        dtype=float,
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
flat = np.asarray(value, dtype=float).reshape(-1)
print("\n".join("%.17g" % item for item in flat))
print("%.17g" % statistics.median(elapsed))
