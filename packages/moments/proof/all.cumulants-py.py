import json
import math
import statistics
import sys
import time
import warnings

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/moments")
warnings.simplefilter("ignore")

from moments import *


def clean(value):
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, list):
        return [clean(item) for item in value]
    return value


def one():
    return all_cumulants(all_moments([1, 2, 3, 4], order_max=5))


value = clean(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if not isinstance(value, list):
    value = [value]
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
