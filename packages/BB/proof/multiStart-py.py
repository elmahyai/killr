import numpy as np
from BB import multi_start
def sys(x):
    return np.array([x[0] - 1.0, x[1] - 2.0])
def one():
    res = multi_start(np.array([[0.0, 0.0], [4.0, -1.0]]), sys, action="solve", control={"trace": False, "NM": False}, quiet=True)
    par = np.ravel(res["par"], order="F")
    return np.concatenate([par, res["fvalue"], res["converged"].astype(float)])
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
