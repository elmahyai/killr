import numpy as np
from BB import bb_solve
def sys(x):
    return np.array([x[0] - 1.0, x[1] - 2.0])
def one():
    res = bb_solve([0.0, 0.0], sys, control={"trace": False}, quiet=True)
    return np.concatenate([res["par"], [res["residual"], res["fn.reduction"], res["feval"], res["iter"], res["convergence"]], res["cpar"]])
import statistics
import time
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
arr = __import__("numpy").atleast_1d(__import__("numpy").asarray(value, dtype=float))
print(",".join("%.17g" % float(v) for v in arr))
print("MS")
print("%.17g" % statistics.median(elapsed))
