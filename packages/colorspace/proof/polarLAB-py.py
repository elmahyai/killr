import statistics, time, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from colorspace.polar_lab import polarLAB
def one(): return polarLAB([50, 60], [20, 30], [10, 200]).coords.tolist()
value = one(); times = []
for _ in range(20):
    t = time.perf_counter(); one(); times.append((time.perf_counter()-t)*1000)
result = {"value": value, "median_ms": statistics.median(times)}
Path(__file__).resolve().parents[1].joinpath("docs/output/polarLAB-python.txt").write_text(str(result) + "\n")
print(result)
