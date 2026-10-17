import json
import statistics
import time
from exactextractr.rasterize_polygons import rasterize_polygons

def one():
    polys = ["POLYGON ((0 0, 2 0, 2 2, 0 2, 0 0))", "POLYGON ((1 1, 3 1, 3 3, 1 3, 1 1))"]
    grid = {"xmin": 0, "xmax": 3, "ymin": 0, "ymax": 3, "nrows": 3, "ncols": 3}
    return rasterize_polygons(polys, grid)["values"]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
shown = [" ".join("NA" if item is None else str(int(item)) for item in row) for row in value]
print(json.dumps({"value": shown, "median_ms": statistics.median(elapsed)}))
