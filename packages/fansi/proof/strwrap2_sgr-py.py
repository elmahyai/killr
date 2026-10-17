import json
import statistics
import time
from fansi.strwrap_ctl import strwrap2_sgr

def one():
    return strwrap2_sgr("\033[31mabcdefghij\033[0m", 6, wrap_always=True, warn=False)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
