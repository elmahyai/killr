import json
import statistics
import time
from fansi.normalize_state import normalize_state

def one():
    return normalize_state("\033[4mhello\033[42;33m world\033[m", warn=False, term_cap=["bright", "256"])

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
