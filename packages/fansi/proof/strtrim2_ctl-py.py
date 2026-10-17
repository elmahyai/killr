import json
import statistics
import time
from fansi.strtrim_ctl import strtrim2_ctl

def one():
    return strtrim2_ctl("a\tbcd", 4, tabs_as_spaces=True, warn=False)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
