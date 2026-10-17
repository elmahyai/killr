import statistics, time, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from colorspace.whitepoint import whitepoint
def one():
    old = whitepoint(); a = whitepoint(); b = whitepoint(100, 100, 100); c = whitepoint()
    whitepoint(old); return {"a": a.coords.tolist(), "b": b.coords.tolist(), "c": c.coords.tolist()}
value = one(); times = []
for _ in range(20):
    t = time.perf_counter(); one(); times.append((time.perf_counter()-t)*1000)
result = str(value) + "\n" + str(statistics.median(times))
Path(__file__).resolve().parents[1].joinpath("docs/output/whitepoint-python.txt").write_text(result + "\n")
print(result)
