import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.quantile_mclust import quantileMclust

proof_dir = Path(__file__).parent
output_dir = proof_dir.parent / "docs" / "output"
object = {
    "d": 1,
    "G": 2,
    "modelName": "V",
    "parameters": {
        "pro": np.array([0.35, 0.65]),
        "mean": np.array([-0.8, 1.1]),
        "variance": {"sigmasq": np.array([0.7, 1.6])},
    },
}
p = np.array([0.001, 0.1, 0.5, 0.9, 0.999])


def one():
    return quantileMclust(object, p)


value = one()
np.savetxt(output_dir / "quantileMclust-py.txt", value)
reference = np.loadtxt(output_dir / "quantileMclust-r.txt")
max_abs_diff = float(np.max(np.abs(value - reference)))
one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
translated_ms = statistics.median(elapsed)
r_ms = float((proof_dir / "quantileMclust-r-ms.txt").read_text())
print(f"matches {max_abs_diff <= 1e-8}")
print(f"max_abs_diff {max_abs_diff:.17g}")
print(f"r_ms {r_ms:.17g}")
print(f"translated_ms {translated_ms:.17g}")
print(f"speedup {r_ms / translated_ms:.17g}")
