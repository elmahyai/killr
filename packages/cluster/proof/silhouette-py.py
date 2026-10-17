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
    n = len(x)
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            distance = math.dist(x[i], x[j])
            matrix[i][j] = matrix[j][i] = distance
    fit = silhouette(pam(x, 2)["clustering"], dmatrix=matrix)
    return [row[1] for row in fit["widths"]] + [row[2] for row in fit["widths"]]
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
