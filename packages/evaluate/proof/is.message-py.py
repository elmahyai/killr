import json
import statistics
import time
from evaluate import is_message
from evaluate.types import Message, Warning

def one():
    return [int(is_message(Message("a"))), int(is_message(Warning("a")))]
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
