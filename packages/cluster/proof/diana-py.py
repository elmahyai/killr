import json
import math
import statistics
import sys
import time

sys.path[:0] = ["/home/ahmed/killr_projects/killr/packages/cluster"]
from cluster import (
    agnes, clara, coef_hclust, coef_hier, diana, fanny, max_se, medoids,
    mona, pam, silhouette, sort_silhouette,
)
from cluster.twins import as_hclust

def one():
    x = [[0, 0], [0.1, 0], [0.2, 0.1], [5, 5], [5, 6], [5.2, 4.8]]
    fit = diana(x)
    return fit["order"] + fit["height"] + [fit["dc"]]
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
