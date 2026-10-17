import json
import math
import statistics
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/urca")
from urca.johansen import ca_jo
from urca.plotres import plotres

_BIN = Path(__file__).with_name("denmark_sjd.bin")
_OUT = Path("/home/ahmed/killr_projects/killr/packages/urca/docs/output")


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
    series = _denmark_sjd()
    fitted = ca_jo(series, ecdet="const", type="eigen", K=2, spec="longrun", season=4)
    return plotres(fitted)


def _save(result):
    _OUT.mkdir(parents=True, exist_ok=True)
    for index, figure in enumerate(result.figures, start=1):
        figure.savefig(_OUT / f"plotres-python-{index}.svg")


result = one()
_save(result)
value = clean(result.values)
for figure in result.figures:
    plt.close(figure)

elapsed = []
for _ in range(20):
    started = time.perf_counter()
    timed = one()
    elapsed.append((time.perf_counter() - started) * 1000)
    for figure in timed.figures:
        plt.close(figure)

print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
