import json
import statistics
import time
from pathlib import Path

from magrittr.aliases import describe, or_


def one():
    return or_([True, True, False, False], [True, False, True, False])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out = Path('/home/ahmed/killr_projects/killr/packages/magrittr/docs/output/or-python.txt')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('or(c(FALSE, TRUE), c(FALSE, FALSE)) returns FALSE, TRUE.' + "\n")
payload = describe(value)
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
