import json
import statistics
import time
from fansi.substr_ctl import substr_ctl_replace

def hexify(value):
    if value is None:
        return "null"
    if isinstance(value, str):
        return value.encode("utf-8").hex()
    return [hexify(item) for item in value]

def one():
    x = ["\033[42mABC", "\033[34mDEF"]
    out = []
    for value in ("_", "\033[m_", "\033[45m_"):
        out.extend(substr_ctl_replace(x, 2, 2, value, warn=False))
    return out

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": hexify(value), "median_ms": statistics.median(elapsed)}))
