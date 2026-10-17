import json
import statistics
import time
from fansi.make_styles import make_styles

def one():
    names16 = [f"{side}-{index}" for index in range(8) for side in ("fg", "bg")]
    mix = [[0.6, 0.2, 0.2], [0.2, 0.6, 0.2], [0.2, 0.2, 0.6]]
    return make_styles(names16, mix)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
shown = [value] if isinstance(value, str) else value
print(json.dumps({"value": [item.encode("utf-8").hex() if isinstance(item, str) else "null" for item in shown], "median_ms": statistics.median(elapsed)}))
