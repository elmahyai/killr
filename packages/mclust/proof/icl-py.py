import statistics, time
import numpy as np
from mclust.mstep_loglik_icl import icl
x = {"n": 4, "bic": 10., "z": np.array([[.8,.2],[.7,.3],[.2,.8],[.1,.9]])}
one = lambda: icl(x)
value = one(); times = []
for _ in range(20):
    start = time.perf_counter(); one(); times.append((time.perf_counter()-start)*1000)
print(value); print(f"{statistics.median(times):.17g}")
