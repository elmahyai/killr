import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from png.readPNG import readPNG

logo = Path(__file__).resolve().parents[1] / "png" / "img" / "Rlogo.png"


def one():
    img = readPNG(logo)
    flat = img.ravel(order="F")
    return [int(v) for v in img.shape] + [float(v) for v in flat]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
