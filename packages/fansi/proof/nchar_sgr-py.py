import json
import statistics
import time
from fansi import nchar_sgr

def one():
    return nchar_sgr(["\x1b[31m123", "\t\n\n123"], warn=False)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
