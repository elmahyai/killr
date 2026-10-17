import statistics, time, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from colorspace.extract_transparency import extract_transparency
def one(): return {
    "numeric": extract_transparency(["#000000", "#ffffff80", None]),
    "integer": extract_transparency(["#000000", "#ffffff80"], "integer"),
    "character": extract_transparency(["#000000", "#ffffff80"], "character"),
    "default": extract_transparency("#000000", default=.5),
}
value = one(); times = []
for _ in range(20):
    t = time.perf_counter(); one(); times.append((time.perf_counter()-t)*1000)
result = str(value) + "\n" + str(statistics.median(times))
Path(__file__).resolve().parents[1].joinpath("docs/output/extract_transparency-python.txt").write_text(result + "\n")
print(result)
