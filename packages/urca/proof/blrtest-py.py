import json
import math
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/urca")
from urca.blrtest import blrtest
from urca.johansen import ca_jo

_BIN = Path(__file__).with_name("denmark_sjd.bin")


def _denmark_sjd():
    raw = np.fromfile(_BIN, dtype=np.float64)
    return raw.reshape(-1, 4, order="F")


def clean(value):
    if isinstance(value, np.ndarray):
        return clean(value.tolist())
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, list):
        return [clean(item) for item in value]
    return value


def one():
    sjd = _denmark_sjd()
    sjd_vecm = ca_jo(sjd, ecdet="const", type="eigen", K=2, spec="longrun", season=4)
    hd0 = np.array(
        [[-1, 0, 0, 0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
        dtype=float,
    )
    res = blrtest(sjd_vecm, hd0, r=1)
    return np.concatenate(
        [
            [res.teststat, res.pval[0], res.pval[1], res.lambda_[0]],
            np.ravel(res.V, order="F"),
            np.ravel(res.W, order="F"),
        ]
    ).tolist()


value = clean(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
