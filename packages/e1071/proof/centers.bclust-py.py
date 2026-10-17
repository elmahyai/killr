import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path("/home/ahmed/killr_projects/killr")
sys.path[:0] = [
    str(ROOT / "packages/e1071"),
    str(ROOT / "packages/boot"),
    str(ROOT / "packages/class"),
    str(ROOT / "packages/cluster"),
    str(ROOT / "packages/proxy"),
]

from boot.rng import set_seed
from e1071.bclust import bclust
from e1071.bclust_steps import centers_bclust

x = np.array(
    [
        [1, 2], [1.2, 1.8], [1.1, 2.2], [5, 8], [5.5, 7.5],
        [4.8, 8.2], [9, 1], [8.5, 1.5], [8.2, 1.2], [5.2, 7.8],
        [3, 3], [3.1, 2.9], [0.5, 6], [7, 4], [6.5, 3.5],
    ],
    dtype=float,
)
set_seed(1)
bc = bclust(x, 3, iter_base=4, base_centers=4, verbose=False, resample=False)


def one():
    return (
        list(centers_bclust(bc, 2).reshape(-1, order="F"))
        + list(centers_bclust(bc, 3).reshape(-1, order="F"))
        + list(centers_bclust(bc, 4).reshape(-1, order="F"))
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": [float(v) for v in value], "median_ms": statistics.median(elapsed)}))
