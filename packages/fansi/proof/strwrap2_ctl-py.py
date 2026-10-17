import json
import statistics
import time
from fansi.strwrap_ctl import strwrap2_ctl

def one():
    return strwrap2_ctl("hello how are you today", 10, pad_end=".", warn=False)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
