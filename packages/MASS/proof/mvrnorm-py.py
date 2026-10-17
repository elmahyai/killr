import statistics
import time

from mass._r_rng import set_seed
from mass.mvrnorm import mvrnorm


def one():
    set_seed(42)
    return mvrnorm(5, [1, 2], [[10, 3], [3, 2]]).reshape(-1, order="F")


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if isinstance(value, str):
    print(value)
else:
    import numpy as np

    flat = np.asarray(value, dtype=float).reshape(-1)
    print("\n".join("%.17g" % item for item in flat))
print("%.17g" % statistics.median(elapsed))
