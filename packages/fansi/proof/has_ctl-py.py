import json
import statistics
import time
from fansi import has_ctl

def one():
    return has_ctl(["hello world", "hello\nworld", "hello\x1b[31mworld\x1b[m", "\n"], warn=False)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
