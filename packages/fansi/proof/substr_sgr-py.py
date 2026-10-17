import json
import statistics
import time
from fansi.substr_ctl import substr_sgr

def hexify(value):
    if value is None:
        return "null"
    if isinstance(value, str):
        return value.encode("utf-8").hex()
    return [hexify(item) for item in value]

def one():
    return substr_sgr(["\033[42mhello\033[m world", "\033[42mhello\033[m world"], [1, 3], 9, warn=False)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": hexify(value), "median_ms": statistics.median(elapsed)}))
