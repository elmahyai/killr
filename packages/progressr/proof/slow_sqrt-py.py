import json
import statistics
import time

from progressr.demo import slow_sqrt
from progressr.options import set_option

set_option("progressr.enable", True)


def one():
    return {"value": slow_sqrt([1, 4, 9], delay=0)}


ans = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
ans["median_ms"] = statistics.median(elapsed)
print(json.dumps(ans))
