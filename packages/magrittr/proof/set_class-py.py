import json
import statistics
import time
from pathlib import Path

from magrittr.aliases import describe, set_class


def one():
    return set_class([1, 2, 3], "myclass")


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out = Path('/home/ahmed/killr_projects/killr/packages/magrittr/docs/output/set_class-python.txt')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('set_class(c(1, 2, 3), myclass) returns class myclass.' + "\n")
payload = describe(value)
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
