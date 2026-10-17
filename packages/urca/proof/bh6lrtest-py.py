import json
import math
import statistics
import sys
import time
import warnings
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/urca")
from urca.bh6lrtest import bh6lrtest
from urca.johansen import ca_jo

_BIN1 = Path(__file__).with_name("ukpppuip_dat1.bin")
_BIN2 = Path(__file__).with_name("ukpppuip_dat2.bin")


def _uk_data():
    dat1 = np.fromfile(_BIN1, dtype=np.float64).reshape(-1, 5, order="F")
    dat2 = np.fromfile(_BIN2, dtype=np.float64).reshape(-1, 2, order="F")
    return dat1, dat2


def clean(value):
    if isinstance(value, np.ndarray):
        return clean(value.tolist())
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, list):
        return [clean(item) for item in value]
    return value


def one():
    dat1, dat2 = _uk_data()
    h1 = ca_jo(dat1, type="trace", K=2, season=4, dumvar=dat2)
    h6 = np.array(
        [[1, 0, 0], [0, 1, 0], [0, 0, 1], [0, 0, 0], [0, 0, 0]],
        dtype=float,
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = bh6lrtest(h1, h6, r=2, r1=1, conv_val=0.0001, max_iter=50)
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
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
