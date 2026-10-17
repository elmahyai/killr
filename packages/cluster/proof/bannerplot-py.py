import json
import statistics
import sys
import time

sys.path[:0] = ["/home/ahmed/killr_projects/killr/packages/cluster"]
from cluster import (
    agnes, bannerplot, clus_gap, clusplot, ellipsoid_hull, ellipsoid_points,
    pam, pltree, predict_ellipsoid, volume,
)
from cluster._rng import set_seed
from cluster.daisy import daisy

x = [
    [1, 2], [1.2, 1.8], [1.1, 2.2], [5, 8], [5.5, 7.5],
    [4.8, 8.2], [9, 1], [8.5, 1.5], [8.2, 1.2], [5.2, 7.8],
]

def one():
    ban = bannerplot(agnes(x))
    left, right = ban["w"]
    pairs = [value for pair in zip(left, right) for value in pair]
    return pairs + ban["at"] + ban["labels"] + [ban["m"]] + ban["y"]
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
