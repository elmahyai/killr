import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/boot")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/extraDistr")
from statmod.limdil import limdil


def collect(out):
    parts = [np.asarray(out["CI"], dtype=float).reshape(-1, order="F")]
    if "test.difference" in out:
        parts.append(np.asarray(out["test.difference"], dtype=float).reshape(-1))
    if "test.slope.wald" in out:
        parts.append(
            np.concatenate(
                [
                    np.asarray(out["test.slope.wald"], dtype=float).reshape(-1),
                    np.asarray(out["test.slope.lr"], dtype=float).reshape(-1),
                    np.asarray(out["test.slope.score.logdose"], dtype=float).reshape(-1),
                    np.asarray(out["test.slope.score.dose"], dtype=float).reshape(-1),
                ]
            )
        )
    return np.concatenate(parts)


def one():
    dose = np.array([50, 100, 200, 400, 800], dtype=float)
    responses = np.array([2, 6, 9, 15, 21], dtype=float)
    tested = np.array([24, 24, 24, 24, 24], dtype=float)
    g1 = collect(limdil(responses, dose, tested, test_unit_slope=True))
    responses2 = np.concatenate([responses, np.array([1, 3, 5, 8, 12], dtype=float)])
    dose2 = np.concatenate([dose, dose])
    tested2 = np.concatenate([tested, tested])
    group2 = np.array([1, 1, 1, 1, 1, 2, 2, 2, 2, 2], dtype=float)
    g2 = collect(
        limdil(
            responses2,
            dose2,
            tested2,
            group=group2,
            test_unit_slope=True,
        )
    )
    g3 = collect(
        limdil(
            np.array([0, 2, 6, 9, 15], dtype=float),
            dose,
            tested,
            test_unit_slope=False,
        )
    )
    return np.concatenate([g1, g2, g3])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(",".join("%.17g" % float(x) for x in np.asarray(value, dtype=float)))
print("MS")
print("%.17g" % statistics.median(elapsed))
