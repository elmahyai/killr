import json
import statistics
import sys
import time

sys.path[:0] = ["/home/ahmed/killr_projects/killr/packages/cluster"]
from cluster import daisy, lower_to_upper_tri_inds, meanabsdev, size_diss, upper_to_lower_tri_inds

rows = [[1, 2], [3, 6], [4, 8], [7, 1]]

def one():
    return [meanabsdev([1, 2, 3, 8])]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if not isinstance(value, list):
    value = [value]
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
