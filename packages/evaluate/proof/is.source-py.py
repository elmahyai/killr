import json
import statistics
import time
from evaluate import evaluate, is_source

def one():
    ev = evaluate("# x", envir={})
    return [int(is_source(ev[0])), int(is_source("x"))]
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
