import json
import statistics
import time
from fansi.to_html import to_html

def one():
    return to_html("hello\033[31;42;1mworld\033[m", warn=False)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
shown = [value] if isinstance(value, str) else value
print(json.dumps({"value": [item.encode("utf-8").hex() if isinstance(item, str) else "null" for item in shown], "median_ms": statistics.median(elapsed)}))
