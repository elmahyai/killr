import json
import statistics
import sys
import time

import numpy as np

sys.path[:0] = [
    "/home/ahmed/killr_projects/killr/packages/e1071",
    "/home/ahmed/killr_projects/killr/packages/zoo",
]
from e1071.stft import stft


def one():
    n = 500
    x = np.sin(np.arange(1, n + 1) / 10) + 0.25 * np.cos(np.arange(1, n + 1) / 7)
    fit = stft(x)
    values = np.asarray(fit["values"], dtype=float).reshape(-1, order="F")
    return list(values) + [fit["windowsize"], fit["increment"]]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if not isinstance(value, list):
    value = [value]
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
