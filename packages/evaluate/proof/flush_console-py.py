import json
import statistics
import time
from evaluate import evaluate

def one():
    source = 'test <- function() { cat("hi"); flush_console(); cat("bye") }'
    env = {}
    evaluate(source, envir=env)
    ev = evaluate("test()", envir=env)
    return [item for item in ev if isinstance(item, str)]
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
