import statistics, time, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from colorspace.protan import protan
def one(): return protan(["#005000", "blue", "#00BB00"], severity=.6)
value = one(); times = []
for _ in range(20):
    t = time.perf_counter(); one(); times.append((time.perf_counter()-t)*1000)
result = ",".join(value) + "\n" + str(statistics.median(times))
Path(__file__).resolve().parents[1].joinpath("docs/output/protan-python.txt").write_text(result + "\n")
print(result)
