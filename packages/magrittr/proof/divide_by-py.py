import json
import statistics
import time
from pathlib import Path

from magrittr.aliases import describe, divide_by


def one():
    return divide_by([1, 2, 3], 2)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out = Path('/home/ahmed/killr_projects/killr/packages/magrittr/docs/output/divide_by-python.txt')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('divide_by(3, 2) returns 1.5.' + "\n")
payload = describe(value)
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
