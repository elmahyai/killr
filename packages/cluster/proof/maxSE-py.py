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
    f = [0.1, 0.4, 0.35, 0.5]
    se = [0.05, 0.05, 0.05, 0.05]
    return [max_se(f, se, name) for name in ("firstmax", "globalmax", "Tibs2001SEmax", "firstSEmax", "globalSEmax")]
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
