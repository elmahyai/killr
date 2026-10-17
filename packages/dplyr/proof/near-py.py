import json
import math
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dplyr.near import near

out = Path(__file__).resolve().parents[1] / "docs" / "output" / "near-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(
    "\n".join(
        [
            repr(math.sqrt(2) ** 2 == 2),
            repr(near(math.sqrt(2) ** 2, 2)),
        ]
    )
    + "\n",
    encoding="utf-8",
)


def encode(value):
    return [None if item is None else (1 if item else 0) for item in value]


# Same eight-value pattern as near-r.R, repeated 2500 times.
x = [math.sqrt(2) ** 2, 1.0, None, float("nan"), float("inf"), float("-inf"), 1e16, 0.0] * 2500
y = [2.0, 1.0 + 1e-9, 1.0, 1.0, float("inf"), float("inf"), 1e16 + 10, 0.0] * 2500


def one():
    return near(x, y)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": encode(value), "median_ms": statistics.median(elapsed)}))
