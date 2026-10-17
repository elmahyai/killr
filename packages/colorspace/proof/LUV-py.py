import json
import statistics
import time

import numpy as np

from colorspace.luv import LUV

MATRIX = np.array(
    [[50, 0, 0], [50, 30, 0], [50, 60, 0]],
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
        "example": LUV(lightness, 0, 0),
        "matrix": LUV((MATRIX, ("a", "b", "c"))),
        "named": LUV([50, 60, 70], 0, 0, names=("x", "y", "z")),
        "integer_l": LUV(np.array([50, 60], dtype=np.int32), 0, 0),
        "scalar": LUV(50.123456789, 10.5, -20.25),
        "empty": LUV(),
        "bulk": LUV(np.linspace(0, 100, 256), 0, 0),
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
