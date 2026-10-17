import numpy as np
from BB import project_linear
A = np.array([[1.0, 1.0], [1.0, 0.0]])
b = np.array([3.0, 0.0])
def one():
    return project_linear([0.2, 0.2], A, b, 0)
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
