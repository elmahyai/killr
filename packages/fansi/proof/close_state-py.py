import json
import statistics
import time
from fansi.state_at_end import close_state

def one():
    return close_state(["\033[44m", "\033[33;44m"], normalize=True, warn=False)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
