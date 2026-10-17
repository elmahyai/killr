import json
import statistics
import time
from evaluate import evaluate, new_output_handler

def one():
    handler = new_output_handler(value=lambda x: x)
    ev = evaluate("1 + 1", envir={}, output_handler=handler)
    return ev[-1]
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
