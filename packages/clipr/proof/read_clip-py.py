import json
import statistics
import time

from clipr import read_clip, write_clip

write_clip(["Write", "to", "clipboard"])


def one():
    return read_clip()


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
