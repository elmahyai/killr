import json
import statistics
import time
from fansi.strwrap_ctl import strwrap_sgr

def one():
    return strwrap_sgr("hello \033[31mred\033[39m world", 12, warn=False)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
