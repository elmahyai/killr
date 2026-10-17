import json
import math
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/urca")
from urca.ca_po import ca_po


def clean(value):
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, list):
        return [clean(item) for item in value]
    return value


ecb_data = np.loadtxt(Path(__file__).with_name("ecb-capo.txt"))


def one():
    obj = ca_po(ecb_data, type="Pz")
    estimates = []
    standard_errors = []
    for summary in obj.testreg:
        table = summary["coefficients"]
        estimates.extend(table[:, 0].tolist())
        standard_errors.extend(table[:, 1].tolist())
    return (
        [float(obj.teststat), float(obj.lag)]
        + [float(v) for v in obj.cval.ravel()]
        + estimates
        + standard_errors
    )


value = clean(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
