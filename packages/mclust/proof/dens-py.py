import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.density import dens

proof_dir = Path(__file__).parent
data = np.array([[-1.2], [-0.1], [0.7], [1.9], [2.4], [3.1]])
parameters = {
    "pro": np.array([0.35, 0.65]),
    "mean": np.array([[-0.4, 1.5]]),
    "variance": {
        "modelName": "EII",
        "d": 1,
        "G": 2,
        "sigmasq": 0.8,
    },
}


def one():
    return dens(data, "EII", parameters)


value = one()
np.savetxt(proof_dir / "dens-py-output.txt", value)
reference = np.loadtxt(proof_dir / "dens-r-output.txt")
max_abs_diff = float(np.max(np.abs(value - reference)))
one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(f"matches {max_abs_diff <= 1e-8}\nmax_abs_diff {max_abs_diff:.17g}")
print(f"translated_ms {statistics.median(elapsed):.17g}")
