import importlib.util
import json
import math
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/extraDistr")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/boot")
from boot.rng import set_seed

_RDIRICHLET_PATH = "/home/ahmed/killr_projects/killr/packages/gtools/gtools/rdirichlet.py"
_spec = importlib.util.spec_from_file_location("gtools_rdirichlet", _RDIRICHLET_PATH)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
rdirichlet = _mod.rdirichlet


def flat(x):
    array = np.asarray(x, dtype=np.float64).reshape(-1, order="F")
    if array.size == 0:
        return ""

    def fmt(v):
        value = float(v)
        if math.isnan(value):
            return "NA"
        if math.isinf(value):
            return "Inf" if value > 0 else "-Inf"
        return format(value, ".16g")

    return "|".join(fmt(v) for v in array)


def one():
    set_seed(4242)
    main = flat(rdirichlet(20, [1, 1, 1]))
    set_seed(4242)
    wide = flat(rdirichlet(5, [0.5, 2, 4, 8]))
    set_seed(777)
    single = flat(rdirichlet(1, [3, 1, 1]))
    return "|".join([main, wide, single])


set_seed(0)
rdirichlet(1, [1.0])
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
