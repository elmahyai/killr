import json
import statistics
import time
from fansi.substr_ctl import substr2_ctl_replace

def hexify(value):
    if value is None:
        return "null"
    if isinstance(value, str):
        return value.encode("utf-8").hex()
    return [hexify(item) for item in value]

def one():
    x = ["\uFF37n\uFF37", "\uFF37" + "e\u0301" + "\uFF37"]
    return substr2_ctl_replace(x, 2, 4, "n", type="width", round="start", warn=False)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": hexify(value), "median_ms": statistics.median(elapsed)}))
