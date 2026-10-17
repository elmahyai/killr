import json
import statistics
import time
from fansi import nchar_ctl

def one():
    return nchar_ctl(["\x1b[31m123\a\r", "\x1b[31m\u4e00\u4e01\u4e03\a\r", "hello\u0300\u035c world", "A\u030a", "\U0001f468\u200d\U0001f469\u200d\U0001f467", "\U0001f1fa\U0001f1f8", "\t\n\r"], type="width", warn=False)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
