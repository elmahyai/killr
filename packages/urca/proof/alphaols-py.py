import json
import math
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/urca")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/vars")
from urca.johansen import alphaols, ca_jo
from vars import Canada


def clean(value):
    if isinstance(value, np.ndarray):
        return clean(value.tolist())
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, list):
        return [clean(item) for item in value]
    return value


def one():
    jo = ca_jo(Canada(), type="trace", ecdet="const", K=2, spec="longrun")
    fit = alphaols(jo)
    fit1 = alphaols(jo, reg_number=1)
    return np.concatenate(
        [np.ravel(fit.coef, order="F"), np.ravel(fit1.coef, order="F")]
    ).tolist()


value = clean(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
