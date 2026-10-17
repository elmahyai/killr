import json
import statistics
import time
from pathlib import Path

from magrittr.aliases import and_, describe


def one():
    return and_([True, True, False, False], [True, False, True, False])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out = Path('/home/ahmed/killr_projects/killr/packages/magrittr/docs/output/and-python.txt')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('and(c(TRUE, FALSE), c(TRUE, TRUE)) returns TRUE, FALSE.' + "\n")
payload = describe(value)
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
