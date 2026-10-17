import json
import statistics
import time

from pillar.extent import get_extent


def one():
    return get_extent(["abc", "de", "運氣", "\033[31mabc\033[39m", "a\tb", None])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
