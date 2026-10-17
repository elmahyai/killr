import json
import statistics
import time
from pathlib import Path

from magrittr.aliases import describe, multiply_by


def one():
    return multiply_by([2, 3, 4, 5], [10, 0.5])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out = Path('/home/ahmed/killr_projects/killr/packages/magrittr/docs/output/multiply_by-python.txt')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('multiply_by(4, 3) returns 12.' + "\n")
payload = describe(value)
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
