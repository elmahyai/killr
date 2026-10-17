import json
import statistics
import time

from crayon import *
options(**{"crayon.enabled": True, "width": 80})

def one():
    make_style(**{"new_style": "maroon"}, bg=True)
    drop_style("new_style")
    return "new_style" in styles()

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
