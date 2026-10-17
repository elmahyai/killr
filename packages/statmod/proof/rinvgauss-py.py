import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/boot")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/extraDistr")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")

from boot.rng import set_seed
from statmod.rinvgauss import rinvgauss


def one():
    set_seed(424242)
    return np.concatenate(
        [
            np.asarray(rinvgauss(5, mean=1, dispersion=0.5), dtype=float).reshape(-1),
            np.asarray(rinvgauss(3, mean=[1, 2, 3], dispersion=0.3), dtype=float).reshape(
                -1
            ),
            np.asarray(rinvgauss(2, mean=np.inf, dispersion=1), dtype=float).reshape(-1),
            np.asarray(rinvgauss(2, mean=1, dispersion=np.inf), dtype=float).reshape(-1),
            np.asarray(rinvgauss(2, mean=-1, dispersion=1), dtype=float).reshape(-1),
            np.asarray(rinvgauss(2, mean=1, shape=4), dtype=float).reshape(-1),
            np.asarray(rinvgauss([1, 1, 1]), dtype=float).reshape(-1),
        ]
    )


value = np.ravel(np.asarray(one(), dtype=float), order="F")
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(",".join(f"{float(x):.17g}" for x in value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
