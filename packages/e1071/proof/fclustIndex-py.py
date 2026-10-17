import json
import statistics
import sys
import time

sys.path[:0] = [
    "/home/ahmed/killr_projects/killr/packages/e1071",
    "/home/ahmed/killr_projects/killr/packages/boot",
    "/home/ahmed/killr_projects/killr/crates/cmeans",
]
from boot.rng import set_seed
from e1071.cmeans import cmeans
from e1071.fclust_index import fclust_index


def one():
    x = [
        [0, 0],
        [3, 0],
        [0, 4],
        [6, 6],
        [1, 2],
        [5, 5],
    ]
    centers = [[0, 0], [5, 5], [3, 4]]
    set_seed(4242)
    fit = cmeans(x, centers, iter_max=50, m=2, dist="euclidean", method="cmeans")
    out = fclust_index(fit, x, index="all")
    order = ("fhv", "apd", "pd", "xb", "fs", "pc", "pe", "pre", "si")
    return [out[name] for name in order]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if not isinstance(value, list):
    value = [value]
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
