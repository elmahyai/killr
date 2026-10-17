import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scales.bounds import expand_range

out = Path(__file__).resolve().parents[1] / "docs" / "output" / "expand_range-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(
    "\n".join(
        [
            repr(expand_range([1, 1], mul=0, add=0.6)),
            repr(expand_range([1, 1], mul=1, add=0.6)),
            repr(expand_range([1, 9], mul=0, add=2)),
        ]
    )
    + "\n",
    encoding="utf-8",
)


def one():
    return expand_range([1, 9], mul=0.1, add=2)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
