import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.hommel_test import hommel_test


def one():
    p1 = np.array(
        [
            0.00023889658041298389,
            0.0015705542173236609,
            0.00394833879545331,
            0.0073341468814760447,
            0.0078847387339919806,
            0.037431032862514257,
            0.038936491124331951,
            0.042988796019926667,
            0.082437558099627495,
            0.085612064925953746,
        ]
    )
    r1 = hommel_test(p1).astype(float).reshape(-1)
    p2 = np.array([0.001, 0.01, 0.04, 0.05, 0.06, 0.5])
    r2 = hommel_test(p2, alpha=0.05).astype(float).reshape(-1)
    p3 = np.array([[0.02, 0.9], [0.03, 0.8]])
    r3 = hommel_test(p3, alpha=0.1).astype(float).reshape(-1)
    r4 = hommel_test(np.array([0.05, 0.05, 0.05, 0.05])).astype(float).reshape(-1)
    return np.concatenate([r1, r2, r3, r4])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(",".join("%.17g" % float(v) for v in np.asarray(value, dtype=float)))
print("MS")
print("%.17g" % statistics.median(elapsed))
