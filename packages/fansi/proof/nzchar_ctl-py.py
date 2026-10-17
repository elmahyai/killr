import json
import statistics
import time
from fansi import nzchar_ctl

def one():
    return nzchar_ctl(["\n\x1b[42;31m\x1b[123P\a", "", "a"], warn=False)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
