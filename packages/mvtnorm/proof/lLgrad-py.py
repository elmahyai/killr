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
    from mvtnorm._iface import _RMatrix
    return flat(lLgrad(mvnorm(chol=as_chol(ltMatrices([1.0, 0.3, 1.0], diag=True))), obs=_RMatrix(np.zeros((2, 1)), rownames=['1', '2']))['scale'])

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(" ".join(f"{v:.16g}" for v in flat(value)))
print(f"MS {statistics.median(elapsed):.17g}")
