import statistics
import time
import numpy as np
from mclust.mstep_loglik_icl import mstep

x = np.array([1., 2., 3., 4.])
z = np.array([[.8, .2], [.7, .3], [.2, .8], [.1, .9]])
one = lambda: mstep(x, "E", z)
value = one()
times = []
for _ in range(20):
    start = time.perf_counter(); one(); times.append((time.perf_counter() - start) * 1000)
print(value["parameters"]["mean"])
print(f"{statistics.median(times):.17g}")
