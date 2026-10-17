import json
import statistics
import time
from fansi.strsplit_ctl import strsplit_ctl

def hexify(value):
    if value is None:
        return "null"
    if isinstance(value, str):
        return value.encode("utf-8").hex()
    return [hexify(item) for item in value]

def one():
    return (
        strsplit_ctl("\033[31mhello\033[42m world!", " ", warn=False)[0]
        + strsplit_ctl("\033[31mhello\033[42m\nworld!", "\n", warn=False)[0]
        + strsplit_ctl("\033[31mhello\033[42m\nworld!", "\n", ctl=["all", "nl"], warn=False)[0]
    )

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": hexify(value), "median_ms": statistics.median(elapsed)}))
