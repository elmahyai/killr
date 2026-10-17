import json
import statistics
import time
from pathlib import Path

from magrittr.aliases import Vector, describe, inset


def one():
    return inset(Vector([1, 2, 3, 4], ["a", "b", "c", "d"]), [2, 4], [20, 40])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out = Path('/home/ahmed/killr_projects/killr/packages/magrittr/docs/output/inset-python.txt')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('inset(c(1, 2, 3), 2, 9) returns 1, 9, 3.' + "\n")
payload = describe(value)
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
