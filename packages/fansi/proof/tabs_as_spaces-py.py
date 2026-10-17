import json
import statistics
import time
from fansi.tabs_as_spaces import tabs_as_spaces

def one():
    return tabs_as_spaces("1\t12\t123\t1234\t12345678", warn=False)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
