import json
import statistics
import time
from pathlib import Path

from magrittr.aliases import RList, describe, extract2


def one():
    return extract2(RList([1, [2, 3], 4], ["a", "b", "c"]), 2)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out = Path('/home/ahmed/killr_projects/killr/packages/magrittr/docs/output/extract2-python.txt')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('extract2(list(a = 1, b = 2), 2) returns 2.' + "\n")
payload = describe(value)
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
