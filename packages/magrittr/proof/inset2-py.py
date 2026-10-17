import json
import statistics
import time
from pathlib import Path

from magrittr.aliases import RList, describe, inset2


def one():
    return inset2(RList([1, 2, 3], ["a", "b", "c"]), 2, 99)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out = Path('/home/ahmed/killr_projects/killr/packages/magrittr/docs/output/inset2-python.txt')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('inset2(list(a = 1, b = 2), 2, 9) returns a = 1, b = 9.' + "\n")
payload = describe(value)
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
