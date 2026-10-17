import numpy as np
from quadprog import solve_qp_compact
D = np.eye(3)
d = np.array([0.0, 5.0, 0.0])
A = np.array([[-4.0, 2.0, -2.0], [-3.0, 1.0, 1.0]])
Aind = np.array([[2, 2, 2], [1, 1, 2], [2, 2, 3]])
b = np.array([-8.0, 2.0, 0.0])
def one():
    res = solve_qp_compact(D, d, A, Aind, b)
    return np.concatenate([res["solution"], [res["value"]], res["unconstrained_solution"], res["iterations"], res["Lagrangian"], res["iact"]])
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
