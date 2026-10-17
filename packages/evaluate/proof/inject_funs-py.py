import json
import statistics
import time
from evaluate import evaluate, inject_funs

def one():
    old = inject_funs(f=lambda: 1)
    try:
        ev = evaluate("f()", envir={})
        return ev[1]
    finally:
        inject_funs(old)
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
