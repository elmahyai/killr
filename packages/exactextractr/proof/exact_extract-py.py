import json
import statistics
import time
from exactextractr.exact_extract import exact_extract

def one():
    values = [[1 + r + c * 10 for c in range(10)] for r in range(10)]
    grid = {"values": values, "xmin": 0, "xmax": 10, "ymin": 0, "ymax": 10}
    return exact_extract(grid, "POLYGON ((2 2, 7 6, 4 9, 2 2))", "mean")

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value[0], "median_ms": statistics.median(elapsed)}))
