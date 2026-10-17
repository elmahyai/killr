import json
import statistics
import time
from fansi.trimws_ctl import trimws_ctl

def one():
    return trimws_ctl(" \033[31m\thello world\t\033[39m ", warn=False)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
