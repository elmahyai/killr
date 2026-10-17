import json
import statistics
import time

from pillar.extent import align


def one():
    return [
        align(["abc", "de"], align="left"),
        align(["abc", "de"], align="right"),
        align(["a", None], align="left"),
        align(["a", "bb"], space="ab"),
    ]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
