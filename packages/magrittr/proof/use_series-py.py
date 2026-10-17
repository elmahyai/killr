import json
import statistics
import time
from pathlib import Path

from magrittr.aliases import RList, describe, use_series


def one():
    return use_series(RList([1, [2, 3], 4], ["apple", "banana", "pear"]), "banana")


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out = Path('/home/ahmed/killr_projects/killr/packages/magrittr/docs/output/use_series-python.txt')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('use_series(list(banana = c(2, 3)), banana) returns 2, 3.' + "\n")
payload = describe(value)
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
