import json
import statistics
import time
from evaluate import is_error
from evaluate.types import Error, Warning

def one():
    return [int(is_error(Error("a"))), int(is_error(Warning("a")))]
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
