import json
import statistics
import time
from pathlib import Path

from magrittr.aliases import describe, raise_to_power


def one():
    return raise_to_power([2, 3, 4], [3, 2, 0.5])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out = Path('/home/ahmed/killr_projects/killr/packages/magrittr/docs/output/raise_to_power-python.txt')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('raise_to_power(2, 3) returns 8.' + "\n")
payload = describe(value)
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
