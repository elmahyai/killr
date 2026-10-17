import json
import statistics
import time
from pathlib import Path

from magrittr.aliases import describe, not_


def one():
    return not_([0, 2, 1])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out = Path('/home/ahmed/killr_projects/killr/packages/magrittr/docs/output/not-python.txt')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('not(c(TRUE, FALSE)) returns FALSE, TRUE.' + "\n")
payload = describe(value)
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
