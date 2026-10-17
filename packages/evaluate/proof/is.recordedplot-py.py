import json
import statistics
import time
from evaluate import evaluate, is_recordedplot

def one():
    ev = evaluate("plot(1)", envir={})
    return [int(is_recordedplot(ev[1])), int(is_recordedplot(1))]
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
