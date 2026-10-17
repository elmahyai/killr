import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/mclust")
from mclust.cdens_x_xii_xxi import cdens_x

proof_dir = Path(__file__).parent
output_dir = proof_dir.parent / "docs" / "output"
n, p = 40, 3
x = np.zeros((n, p))
for i in range(1, n + 1):
    for j in range(1, p + 1):
        x[i - 1, j - 1] = ((i * 7 + j * 13) % 17) / 17 - 0.5 + 0.05 * i * j / n
xv = x[:, 0]
parameters = {"mean": np.array([-0.4, 0.1, 0.6]), "variance": {"modelName": "X", "sigmasq": 0.9}}


def one():
    return cdens_x(xv, parameters, logarithm=False)


value = one()
np.savetxt(output_dir / "cdensX-py.txt", value, fmt="%.17g")
reference = np.loadtxt(output_dir / "cdensX-r.txt")
max_abs_diff = float(np.max(np.abs(value - reference))) if value.shape == reference.shape else float("inf")
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
translated_ms = statistics.median(elapsed)
r_ms = float((proof_dir / "cdensX-r-ms.txt").read_text())
print(f"matches {max_abs_diff <= 1e-8}")
print(f"max_abs_diff {max_abs_diff:.17g}")
print(f"translated_ms {translated_ms:.17g}")
print(f"r_ms {r_ms:.17g}")
print(f"speedup {r_ms / translated_ms:.17g}")
