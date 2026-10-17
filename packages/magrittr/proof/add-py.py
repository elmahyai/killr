import json
import statistics
import time
from pathlib import Path

from magrittr.aliases import Vector, add, describe


def one():
    return add(Vector([1, 2, 3, 4], ["a", "b", "c", "d"]), [10, 20])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out = Path('/home/ahmed/killr_projects/killr/packages/magrittr/docs/output/add-python.txt')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('add(2, 3) returns 5.' + "\n")
payload = describe(value)
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
