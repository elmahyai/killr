import statistics, time, sys
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/mclust")
from mclust.as_mclust import as_mclust_default
x = {"G": 2, "_class":["Mclust"]}
one = lambda: as_mclust_default(x)["G"]
value = one(); elapsed=[]
for _ in range(20):
    t0=time.perf_counter(); one(); elapsed.append((time.perf_counter()-t0)*1000)
print("%.17g" % value); print("%.17g" % statistics.median(elapsed))
