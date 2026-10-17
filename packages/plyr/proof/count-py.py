import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from plyr.count import count

n = 20000
letters = [chr(ord("A") + k) for k in range(26)]
year = []
team = []
g = []
for i in range(1, n + 1):
    year.append(1871 + (i % 50))
    team.append(letters[(i // 50) % 26])
    g.append((i * 13) % 160 + 1)
frame = {"year": year, "team": team, "g": g}


def one():
    return count(frame, ["year", "team"], "g")


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

parts = []
for y, label, freq in zip(value.columns["year"], value.columns["team"], value.columns["freq"]):
    parts.append(f"{y}|{label}|{format(float(freq), '.17g')}")
print("VALUE " + ";".join(parts))
print(f"MS {statistics.median(elapsed):.17g}")
