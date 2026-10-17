import json
import statistics
import time

import numpy as np

from colorspace.lab import LAB

MATRIX = np.array(
    [[50, 0, 0], [50, 30, 0], [50, 60, 0]],
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
    lightness = np.linspace(0, 100, 13)[:-1]
    return {
        "example": LAB(lightness, 0, 0),
        "matrix": LAB((MATRIX, ("a", "b", "c"))),
        "named": LAB([50, 60, 70], 0, 0, names=("x", "y", "z")),
        "integer_l": LAB(np.array([50, 60], dtype=np.int32), 0, 0),
        "scalar": LAB(50.123456789, 10.5, -20.25),
        "empty": LAB(),
        "bulk": LAB(np.linspace(0, 100, 256), 0, 0),
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
