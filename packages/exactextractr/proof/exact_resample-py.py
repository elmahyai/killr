import json
import statistics
import time
from exactextractr.exact_resample import exact_resample

def one():
    src = {"values": [[1 + r + c * 4 for c in range(4)] for r in range(4)], "xmin": 0, "xmax": 4, "ymin": 0, "ymax": 4}
    dst = {"xmin": 0, "xmax": 4, "ymin": 0, "ymax": 4, "nrows": 2, "ncols": 2}
    return exact_resample(src, dst, "mean")["values"]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
shown = [" ".join(format(item, ".17g") for item in row) for row in value]
print(json.dumps({"value": shown, "median_ms": statistics.median(elapsed)}))
