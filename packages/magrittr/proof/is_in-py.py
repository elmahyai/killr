import json
import statistics
import time
from pathlib import Path

from magrittr.aliases import describe, is_in


def one():
    return is_in([1, 3, 5, 3], [3, 5, 7])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out = Path('/home/ahmed/killr_projects/killr/packages/magrittr/docs/output/is_in-python.txt')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('is_in(c(1, 3), c(3, 5)) returns FALSE, TRUE.' + "\n")
payload = describe(value)
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
