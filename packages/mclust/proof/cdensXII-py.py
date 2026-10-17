import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/mclust")
from mclust.cdens_x_xii_xxi import cdens_xii

proof_dir = Path(__file__).parent
output_dir = proof_dir.parent / "docs" / "output"
n, p, G = 40, 3, 3
x = np.zeros((n, p))
for i in range(1, n + 1):
    for j in range(1, p + 1):
        x[i - 1, j - 1] = ((i * 7 + j * 13) % 17) / 17 - 0.5 + 0.05 * i * j / n
mu = np.zeros((p, G))
for j in range(1, p + 1):
    for k in range(1, G + 1):
        mu[j - 1, k - 1] = 0.3 * k - 0.2 * j + 0.1 * j * k
parameters = {"mean": mu, "variance": {"modelName": "XII", "sigmasq": 0.9}}


def one():
    return cdens_xii(x, parameters, logarithm=False)


value = one()
np.savetxt(output_dir / "cdensXII-py.txt", value, fmt="%.17g")
reference = np.loadtxt(output_dir / "cdensXII-r.txt")
max_abs_diff = float(np.max(np.abs(value - reference))) if value.shape == reference.shape else float("inf")
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
translated_ms = statistics.median(elapsed)
r_ms = float((proof_dir / "cdensXII-r-ms.txt").read_text())
print(f"matches {max_abs_diff <= 1e-8}")
print(f"max_abs_diff {max_abs_diff:.17g}")
print(f"translated_ms {translated_ms:.17g}")
print(f"r_ms {r_ms:.17g}")
print(f"speedup {r_ms / translated_ms:.17g}")
