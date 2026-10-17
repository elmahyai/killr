import json
import statistics
import time
from pathlib import Path

from magrittr.aliases import Vector, describe, subtract


def one():
    return subtract(Vector([5, 1], ["a", "b"]), [2, 3])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out = Path('/home/ahmed/killr_projects/killr/packages/magrittr/docs/output/subtract-python.txt')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('subtract(5, 2) returns 3.' + "\n")
payload = describe(value)
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
