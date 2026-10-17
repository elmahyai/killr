import json
import statistics
import time
from fansi.state_at_end import state_at_end

def one():
    return state_at_end(["\033[44mhello", "\033[33mworld"], carry=True, normalize=True, warn=False, term_cap=["bright", "256"])

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
