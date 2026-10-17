import json
import statistics
import time
import warnings

from clipr import clear_clip, read_clip, write_clip

write_clip("to-clear")


def one():
    return clear_clip()


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    emptied = read_clip()

print(json.dumps({
    "value": value,
    "empty": emptied is None,
    "median_ms": statistics.median(elapsed),
}))
