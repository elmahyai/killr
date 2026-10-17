import statistics, sys, time
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/mclust")
from mclust.count import count
def one(): return count([1, 2, 1, 3, 2], [1, 2, 3])
value = one(); elapsed = []
for _ in range(20):
    t0 = time.perf_counter(); one(); elapsed.append((time.perf_counter()-t0)*1000)
for x in value: print("%.17g" % x)
print("%.17g" % statistics.median(elapsed))
