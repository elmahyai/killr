import json
import statistics
import time

import numpy as np

from colorspace.rgb import RGB

MATRIX = np.array(
    [[0, 0, 0], [0.3, 1, 1], [0.6, 1, 1]],
    dtype=np.float64,
)


def _block(color):
    names = None if color.names is None else list(color.names)
    columns = [] if color.coords.size == 0 else list(color.columns)
    return {
        "space": color.space,
        "names": names,
        "columns": columns,
        "coords": color.coords.tolist(),
    }


def one():
    reds = np.linspace(0, 1, 13)[:-1]
    return {
        "example": RGB(reds, 0, 0),
        "matrix": RGB((MATRIX, ("a", "b", "c"))),
        "named": RGB([0, 0.3, 0.6], 0, 1, names=("x", "y", "z")),
        "integer_r": RGB(np.array([0, 1], dtype=np.int32), 0, 0),
        "scalar": RGB(0.123456789, 0.5, 0.25),
        "empty": RGB(),
        "bulk": RGB(np.linspace(0, 1, 256), 0, 0),
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
