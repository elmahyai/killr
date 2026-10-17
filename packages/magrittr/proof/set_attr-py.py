import json
import statistics
import time
from pathlib import Path

from magrittr.aliases import describe, set_attr


def one():
    return set_attr([1, 2, 3], "color", "red")


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out = Path('/home/ahmed/killr_projects/killr/packages/magrittr/docs/output/set_attr-python.txt')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('set_attr(c(1, 2, 3), color, red) returns color red.' + "\n")
payload = describe(value)
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
