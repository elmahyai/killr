import contextlib
import io
import json
import math
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/urca")
from urca.johansen import ca_jo
from urca.lttest import lttest

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
    with contextlib.redirect_stdout(io.StringIO()):
        res = lttest(sjd_vecm, r=1)
    return [float(res[0, 0]), float(res[0, 1])]


value = clean(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    with contextlib.redirect_stdout(io.StringIO()):
        one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
