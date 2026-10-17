import json
import statistics
import time

import numpy as np

from colorspace.hsv import HSV

MATRIX = np.array(
    [[0, 1, 1], [30, 1, 1], [60, 1, 1]],
    dtype=np.float64,
)


def _block(color):
    names = None if color.names is None else list(color.names)
    return {
        "space": color.space,
        "names": names,
        "columns": list(color.columns),
        "coords": color.coords.tolist(),
    }


def one():
    hues = np.linspace(0, 360, 13)[:-1]
    return {
        "example": HSV(hues, 1, 1),
        "matrix": HSV((MATRIX, ("a", "b", "c"))),
        "named": HSV([0, 30, 60], 1, 1, names=("x", "y", "z")),
        "integer_h": HSV(np.array([0, 30], dtype=np.int32), 1, 1),
        "scalar": HSV(0.123456789, 1, 1),
        "empty": HSV(),
        "bulk": HSV(np.linspace(0, 360, 256), 1, 1),
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
