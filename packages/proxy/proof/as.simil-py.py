import json
import statistics
import sys
import time

sys.path[:0] = ["/home/ahmed/killr_projects/killr/packages/proxy"]
from proxy.dist import (
    as_dist, as_matrix, as_simil, col_dist, colMeans_dist, colSums_dist,
    dist, pr_DB, pr_dist2simil, pr_simil2dist, row_dist, rowMeans_dist,
    rowSums_dist, simil,
)

def one():
    x = [[1, 2], [3, 6], [4, 8], [7, 1]]
    return list(as_simil(as_matrix(simil(x, method="cosine"))))
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
