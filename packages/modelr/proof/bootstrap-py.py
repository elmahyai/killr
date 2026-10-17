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
    set_seed(1)
    drawn = bootstrap(mtcars, 3)
    return list(drawn["strap"][0].idx[:8]) + [len(drawn[".id"][0]), int(drawn[".id"][0])]


value = clean(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if not isinstance(value, list):
    value = [value]
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
