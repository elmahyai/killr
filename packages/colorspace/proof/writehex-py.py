import statistics, tempfile, time, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from colorspace.srgb import sRGB
from colorspace.writehex import writehex
def one():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "colors.txt"
        writehex(sRGB([1, 0, .25], [0, 1, .5], [0, 0, .75]), p)
        return p.read_text().strip().replace("\n", "|")
value = one(); times = []
for _ in range(20):
    t = time.perf_counter(); one(); times.append((time.perf_counter()-t)*1000)
result = value + "\n" + str(statistics.median(times))
Path(__file__).resolve().parents[1].joinpath("docs/output/writehex-python.txt").write_text(result + "\n")
print(result)
