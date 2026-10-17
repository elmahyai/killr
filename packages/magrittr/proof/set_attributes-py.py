import json
import statistics
import time
from pathlib import Path

from magrittr.aliases import describe, set_attributes


def one():
    return set_attributes([1, 2, 3], {"names": ["a", "b", "c"], "color": "red"})


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out = Path('/home/ahmed/killr_projects/killr/packages/magrittr/docs/output/set_attributes-python.txt')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('set_attributes(c(1, 2, 3), list(names = c(a, b, c), color = red)) returns a = 1, b = 2, c = 3 with color red.' + "\n")
payload = describe(value)
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
