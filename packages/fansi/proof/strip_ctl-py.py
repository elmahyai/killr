import json
import statistics
import time
from fansi import strip_ctl

def one():
    return strip_ctl("hello\x1bk\x1b[45p world\n\x1b[31mgoodbye\a moon", warn=False)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
