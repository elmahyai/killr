import json
import statistics
import time
from pathlib import Path

from magrittr.aliases import describe, divide_by_int


def one():
    return divide_by_int([-7, 7, -8, 8], [2, -3])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out = Path('/home/ahmed/killr_projects/killr/packages/magrittr/docs/output/divide_by_int-python.txt')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('divide_by_int(-7, 2) returns -4.' + "\n")
payload = describe(value)
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
