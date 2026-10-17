import statistics, time
from mclust.mstep_loglik_icl import print_mclust_loglik
x = {"value": -12.3, "df": 5, "nobs": 10}
one = lambda: print_mclust_loglik(x)
value = one(); times = []
for _ in range(20):
    start = time.perf_counter(); one(); times.append((time.perf_counter()-start)*1000)
print(value); print(f"{statistics.median(times):.17g}")
