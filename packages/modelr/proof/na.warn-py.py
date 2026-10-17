import json
import math
import statistics
import sys
import time
import warnings

sys.path[:0] = [
    "/home/ahmed/killr_projects/killr/packages/modelr",
    "/home/ahmed/killr_projects/killr/packages/magrittr",
    "/home/ahmed/killr_projects/killr/packages/boot",
]

warnings.simplefilter("ignore")

from boot.rng import set_seed
from modelr import *
from modelr.frame import Factor


def clean(value):
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, list):
        return [clean(item) for item in value]
    return value


def one():
    data = {"x": [1, 2, 3, 4, 5], "y": [1.0, None, 3.0, None, 5.0]}
    return predict(lm("y ~ x", data, na_action=na_warn))


value = clean(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if not isinstance(value, list):
    value = [value]
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
