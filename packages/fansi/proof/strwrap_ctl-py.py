import json
import statistics
import time
from fansi.strwrap_ctl import strwrap_ctl

def one():
    return strwrap_ctl("hello \033[41mred\033[49m world", 12, warn=False)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
