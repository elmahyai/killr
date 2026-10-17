import json
import statistics
import time
from pathlib import Path

from magrittr.aliases import describe, set_names


def one():
    return set_names([1, 2, 3], ["a", "b", "c"])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out = Path('/home/ahmed/killr_projects/killr/packages/magrittr/docs/output/set_names-python.txt')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('set_names(c(1, 2), c(a, b)) returns a = 1, b = 2.' + "\n")
payload = describe(value)
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
