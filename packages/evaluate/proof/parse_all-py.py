import json
import statistics
import time
from evaluate import parse_all
from evaluate.parse import expr_label

def one():
    parsed = parse_all(["# a comment", "x", "x;y", "x;y;z"])
    return list(parsed.src) + [expr_label(exprs) for exprs in parsed.expr]
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
