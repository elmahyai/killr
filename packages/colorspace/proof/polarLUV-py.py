import json
import statistics
import time

import numpy as np

from colorspace.polar_luv import polarLUV

MATRIX = np.array(
    [[50, 80, 0], [50, 80, 180], [50, 80, 360]],
    dtype=np.float64,
)


def _block(color):
    names = None if color.names is None else list(color.names)
    if color.coords.size == 0:
        columns = []
    else:
        columns = list(color.columns)
    return {
        "space": color.space,
        "names": names,
        "columns": columns,
        "coords": color.coords.tolist(),
    }


def one():
    lightness = np.linspace(0, 100, 13)[:-1]
    return {
        "channels": polarLUV(lightness, 80, 0),
        "matrix": polarLUV((MATRIX, ("a", "b", "c"))),
        "empty": polarLUV(),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

payload = {key: _block(color) for key, color in value.items()}
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
