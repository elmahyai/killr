import numpy as np
from BB import bb_optim
def fn(x):
    return np.sum((np.asarray(x, dtype=float) - np.array([1.0, 2.0, 3.0])) ** 2)
def gr(x):
    return 2 * (np.asarray(x, dtype=float) - np.array([1.0, 2.0, 3.0]))
def one():
    res = bb_optim([0.0, 0.0, 0.0], fn, gr, control={"checkGrad": False, "trace": False}, quiet=True)
    return np.concatenate([res["par"], [res["value"], res["gradient"], res["fn.reduction"], res["iter"], res["feval"], res["convergence"]], res["cpar"]])
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
