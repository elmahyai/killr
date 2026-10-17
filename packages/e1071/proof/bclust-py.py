import importlib.util
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
]

for name, rel in [
    ("e1071._cutree", "e1071/_cutree.py"),
    ("e1071._kmns", "e1071/_kmns.py"),
]:
    spec = importlib.util.spec_from_file_location(name, ROOT / "packages/e1071" / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)

spec = importlib.util.spec_from_file_location(
    "e1071.bclust", ROOT / "packages/e1071/e1071/bclust.py"
)
bclust_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bclust_mod)

from boot.rng import set_seed


def one():
    set_seed(4242)
    x = np.array([[0, 0], [3, 0], [0, 4], [6, 6], [1, 2], [5, 5]], dtype=float)
    bc = bclust_mod.bclust(
        x,
        2,
        iter_base=2,
        base_centers=3,
        verbose=False,
        resample=False,
    )
    return (
        list(np.asarray(bc["cluster"], dtype=float))
        + list(np.asarray(bc["centers"], dtype=float).reshape(-1, order="F"))
        + list(np.asarray(bc["allcenters"], dtype=float).reshape(-1, order="F"))
        + list(np.asarray(bc["members"], dtype=float).reshape(-1, order="F"))
        + list(np.asarray(bc["hclust"]["height"], dtype=float))
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
