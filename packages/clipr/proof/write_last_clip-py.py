import json
import statistics
import time

from clipr import write_last_clip


def one():
    return write_last_clip("Write to clipboard", return_new=True)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
