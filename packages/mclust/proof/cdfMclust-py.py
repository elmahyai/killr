import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.cdf_mclust import cdfMclust

proof_dir = Path(__file__).parent
output_dir = proof_dir.parent / "docs" / "output"
object = {
    "data": np.array([-3, -2, -1, 0, 1, 2, 3], dtype=float),
    "G": 2,
    "parameters": {
        "pro": np.array([0.35, 0.65]),
        "mean": np.array([-0.8, 1.1]),
        "variance": {"sigmasq": np.array([0.7, 1.6])},
    },
}
grid = np.array([-3.5, -2.25, -1, 0.25, 1.5, 2.75, 4])


def one():
    return cdfMclust(object, grid)["y"]


value = one()
np.savetxt(output_dir / "cdfMclust-py.txt", value)
reference = np.loadtxt(output_dir / "cdfMclust-r.txt")
max_abs_diff = float(np.max(np.abs(value - reference)))
one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
r_ms = float((proof_dir / "cdfMclust-r-ms.txt").read_text())
print(f"matches {max_abs_diff <= 1e-8}")
print(f"max_abs_diff {max_abs_diff:.17g}")
print(f"translated_ms {statistics.median(elapsed):.17g}")
print(f"r_ms {r_ms:.17g}")
print(f"speedup {r_ms / statistics.median(elapsed):.17g}")
