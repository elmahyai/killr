import json
import statistics
import time
from pathlib import Path

from magrittr.aliases import describe, is_weakly_greater_than


def one():
    return is_weakly_greater_than([1, 2, 3], 2)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out = Path('/home/ahmed/killr_projects/killr/packages/magrittr/docs/output/is_weakly_greater_than-python.txt')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('is_weakly_greater_than(2, 2) returns TRUE.' + "\n")
payload = describe(value)
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
