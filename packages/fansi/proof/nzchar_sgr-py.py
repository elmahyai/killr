import json
import statistics
import time
from fansi import nzchar_sgr

def one():
    return nzchar_sgr(["\x1b[31m", "a", None], warn=False)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
