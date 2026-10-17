import json
import statistics
import time

from clipr import write_clip


def one():
    return write_clip(
        {"a": [1, 2, 3], "b": [4, 5, 6]},
        return_new=True,
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
