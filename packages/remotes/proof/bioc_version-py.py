import json
import statistics
import time

from remotes.bioc import bioc_version


def one():
    return bioc_version("3.4")


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
