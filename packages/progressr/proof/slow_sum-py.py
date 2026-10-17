import json
import statistics
import time

from progressr.demo import slow_sum
from progressr.options import set_option

set_option("progressr.enable", True)


def one():
    value = slow_sum(list(range(1, 11)), delay=0)
    storage = "integer" if type(value) is int else "double"
    return {"value": value, "storage": storage}


ans = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
ans["median_ms"] = statistics.median(elapsed)
print(json.dumps(ans))
