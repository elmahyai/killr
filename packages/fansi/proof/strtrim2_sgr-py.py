import json
import statistics
import time
from fansi.strtrim_ctl import strtrim2_sgr

def one():
    return strtrim2_sgr("\033[32mabcdef\033[0m", 3, warn=False)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
