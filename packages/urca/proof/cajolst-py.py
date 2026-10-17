import json
import math
import statistics
import sys
import time
import warnings
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/urca")
from urca.cajolst import cajolst

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
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = cajolst(sjd, trend=True, K=2, season=4)
    parts = [
        [float(fit.bp)],
        np.ravel(fit.teststat, order="F"),
        np.ravel(fit.lambda_, order="F"),
        np.ravel(fit.V, order="F"),
        np.ravel(fit.W, order="F"),
    ]
    if fit.cval is not None:
        parts.append(np.ravel(fit.cval, order="F"))
    return np.concatenate(parts).tolist()


value = clean(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
