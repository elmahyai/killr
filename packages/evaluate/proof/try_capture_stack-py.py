import json
import statistics
import time
from evaluate import create_traceback, try_capture_stack

def one():
    caught = try_capture_stack('stop("boom")', {})
    return [caught.message, create_traceback(caught.calls)[0][3:]]
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
