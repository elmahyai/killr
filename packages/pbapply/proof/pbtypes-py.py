import json
import statistics
import time

from pbapply.pbtypes import pbtypes


def one():
    return list(pbtypes())


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
