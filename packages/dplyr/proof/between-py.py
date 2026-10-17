import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dplyr._vec import ordered
from dplyr.between import between

out = Path(__file__).resolve().parents[1] / "docs" / "output" / "between-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)
sample = np.random.standard_normal(100)
mask = between(sample.tolist(), -1, 1)
inside = [value for value, keep in zip(sample.tolist(), mask) if keep]
# starwars$height from dplyr 1.2.1. The manual prints filter(); this is between().
heights = [
    172, 167, 96, 202, 150, 178, 165, 97, 183, 182, 188, 180, 228, 180, 173,
    175, 170, 180, 66, 170, 183, 200, 190, 177, 175, 180, 150, None, 88, 160,
    193, 191, 170, 185, 196, 224, 206, 183, 137, 112, 183, 163, 175, 180, 178,
    79, 94, 122, 163, 188, 198, 196, 171, 184, 188, 264, 188, 196, 185, 157,
    183, 183, 170, 166, 165, 193, 191, 183, 168, 198, 229, 213, 167, 96, 193,
    191, 178, 216, 234, 188, 178, 206, None, None, None, None, None,
]
levels = ["low", "medium", "high"]
ordered_x = ordered(["low", "medium", "high", "medium"], levels)
lines = [
    repr(between(list(range(1, 13)), 7, 9)),
    repr(inside),
    repr(between(heights, 100, 150)),
    repr(between(ordered_x, "medium", "high")),
    repr(between(ordered_x, "medium", "high", ptype=ordered_x)),
]
out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def encode(value):
    return [None if item is None else (1 if item else 0) for item in value]


# Same pattern as between-r.R: 1:12, NA, -Inf, Inf, repeated 2000 times.
check_x = list(range(1, 13)) + [None, float("-inf"), float("inf")]
check_x = check_x * 2000


def one():
    return between(check_x, 7, 9)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": encode(value), "median_ms": statistics.median(elapsed)}))
