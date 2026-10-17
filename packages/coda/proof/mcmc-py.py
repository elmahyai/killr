import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coda.mcmc import mcmc

root = Path(__file__).resolve().parent


def one():
    n = 100
    i = np.arange(1, n + 1, dtype=np.float64)
    x = np.column_stack(
        (
            np.sin(i / 3) + 0.2 * np.cos(i),
            np.cos(i / 5) + 0.01 * i,
            np.full(n, 2.0),
        )
    )
    v = np.arange(1, 11, dtype=np.float64)
    obj = mcmc(x)
    obj2 = mcmc(v, end=19, thin=2)
    parts = [
        *np.ravel(np.asarray(obj.data, dtype=np.float64), order="F"),
        *obj.mcpar.tolist(),
        *np.ravel(np.asarray(obj2.data, dtype=np.float64), order="F"),
        *obj2.mcpar.tolist(),
    ]
    return parts


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

(root / "mcmc-py.txt").write_text(
    json.dumps({"value": value, "median_ms": statistics.median(elapsed)}) + "\n"
)
