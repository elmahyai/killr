import json
import statistics
import time
from pathlib import Path

from magrittr.aliases import Vector, describe, extract


def one():
    return extract(Vector([10, 20, 30, 40], ["a", "b", "c", "d"]), [2, 4])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out = Path('/home/ahmed/killr_projects/killr/packages/magrittr/docs/output/extract-python.txt')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('extract(c(10, 20, 30), 2) returns 20.' + "\n")
payload = describe(value)
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
