import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from plyr.rbind_fill import rbind_fill

n = 20000
x = [(i * 3) / 7 for i in range(1, n + 1)]
y = [(i % 11) + 0.5 for i in range(1, n + 1)]
z = [i * 1.25 for i in range(1, n + 1)]
y2 = [(i % 13) / 3 for i in range(1, n + 1)]
frame_a = {"x": x, "y": y}
frame_b = {"y": y2, "z": z}


def one():
    return rbind_fill(frame_a, frame_b)


def show(values):
    parts = []
    for value in values:
        if value is None:
            parts.append("NA")
        else:
            parts.append(float(value).hex())
    return " ".join(parts)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print("NAMES " + " ".join(value.columns))
print("X " + show(value.columns["x"]))
print("Y " + show(value.columns["y"]))
print("Z " + show(value.columns["z"]))
print(f"MS {statistics.median(elapsed):.17g}")
