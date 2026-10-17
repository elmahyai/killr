import math
import statistics
import time
import numpy as np
from boot.rng import set_seed
from mvtnorm import *

def flat(x):
    if isinstance(x, (bool, np.bool_)):
        return np.array([1.0 if x else 0.0])
    return np.atleast_1d(np.asarray(x, dtype=float)).ravel(order="F")

def one():
    return flat(destandardize(chol=as_chol(ltMatrices([2.0, 0.5, 3.0], diag=True)), score_schol=ltMatrices([0.1, 0.2, 0.3], diag=True)))

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(" ".join(f"{v:.16g}" for v in flat(value)))
print(f"MS {statistics.median(elapsed):.17g}")
