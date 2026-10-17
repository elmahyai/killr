import json
import random
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scales.bounds import rescale

out = Path(__file__).resolve().parents[1] / "docs" / "output" / "rescale-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(
    "\n".join(
        [
            repr(rescale(list(range(1, 101)))),
            repr(rescale([random.random() for _ in range(50)])),
            repr(rescale(1)),
        ]
    )
    + "\n",
    encoding="utf-8",
)


def one():
    return rescale([2, None, 0, -2], to=(10, 20))


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
