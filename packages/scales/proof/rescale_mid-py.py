import json
import random
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scales.bounds import rescale_mid

out = Path(__file__).resolve().parents[1] / "docs" / "output" / "rescale_mid-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(
    "\n".join(
        [
            repr(rescale_mid(list(range(1, 101)), mid=50.5)),
            repr(rescale_mid([random.random() for _ in range(50)], mid=0.5)),
            repr(rescale_mid(1)),
        ]
    )
    + "\n",
    encoding="utf-8",
)


def one():
    return rescale_mid([2, None, 0, -2], mid=0.5)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
