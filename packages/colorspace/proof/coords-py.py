import json
import statistics
import time

import numpy as np

from colorspace.coords import coords
from colorspace.hls import HLS
from colorspace.lab import LAB
from colorspace.rgb import RGB

MATRIX_HLS = np.array(
    [[0, 0.5, 1], [30, 0.5, 1], [60, 0.5, 1]], dtype=np.float64
)


def _json_mat(matrix: np.ndarray):
    if matrix.size == 0:
        return []
    return matrix.tolist()


def one():
    return {
        "hls": coords(HLS([0, 30, 60], 0.5, 1)),
        "lab": coords(LAB([50, 60], 10, -20)),
        "rgb": coords(RGB([0.2, 0.4], 0.5, 0.8)),
        "matrix_hls": coords(HLS((MATRIX_HLS, ("a", "b", "c")))),
        "empty": coords(HLS()),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

payload = {key: _json_mat(mat) for key, mat in value.items()}
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
