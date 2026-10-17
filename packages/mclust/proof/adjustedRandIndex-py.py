import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/mclust")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/boot")
from boot.rng import sample_int, set_seed
from mclust.adjusted_rand_index import adjusted_rand_index


def one():
    a = np.tile(np.arange(1, 4), 3)
    b = np.tile(np.array(["A", "B", "C"]), 3)
    v1 = adjusted_rand_index(a, b)
    set_seed(42)
    a2 = np.array(sample_int(3, 9, replace=True), dtype=int)
    labels = np.array(["A", "B", "C"])
    b2 = labels[np.array(sample_int(3, 9, replace=True), dtype=int) - 1]
    v2 = adjusted_rand_index(a2, b2)
    a3 = np.tile(np.arange(1, 4), 4)
    b3 = np.tile(np.array(["A", "B", "C", "D"]), 3)
    v3 = adjusted_rand_index(a3, b3)
    return [v1, v2, v3]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for item in value:
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
