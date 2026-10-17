import statistics, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.hc_variants import hcV
x = [1, 2, 3, 8, 9]
one = lambda: hcV(x, partition=[1, 1, 1, 2, 2])
value = one(); times = []
for _ in range(20):
    t = time.perf_counter(); one(); times.append((time.perf_counter()-t)*1000)
print({"value": value.tolist(), "median_ms": statistics.median(times)})
