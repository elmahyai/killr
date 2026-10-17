import json
import statistics
import time

import numpy as np

from colorspace.hls import HLS

MATRIX = np.array(
    [[0, 0.5, 1], [30, 0.5, 1], [60, 0.5, 1]],
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
        "example": HLS(hues, 0.5, 1),
        "matrix": HLS((MATRIX, ("a", "b", "c"))),
        "named": HLS([0, 30, 60], 0.5, 1, names=("x", "y", "z")),
        "integer_h": HLS(np.array([0, 30], dtype=np.int32), 0.5, 1),
        "scalar": HLS(0.123456789, 0.5, 1),
        "empty": HLS(),
        "bulk": HLS(np.linspace(0, 360, 256), 0.5, 1),
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
