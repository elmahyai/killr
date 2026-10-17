import json
import statistics
import time
from exactextractr.coverage_fraction import coverage_fraction

def one():
    grid = {"xmin": 0, "xmax": 3, "ymin": 0, "ymax": 3, "nrows": 3, "ncols": 3}
    square = "POLYGON ((0.5 0.5, 2.5 0.5, 2.5 2.5, 0.5 2.5, 0.5 0.5))"
    return coverage_fraction(grid, square)[0]["values"]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
shown = [" ".join(format(item, ".17g") for item in row) for row in value]
print(json.dumps({"value": shown, "median_ms": statistics.median(elapsed)}))
