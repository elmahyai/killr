import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coda.as_mcmc import as_mcmc
from coda.raftery_diag import raftery_diag

root = Path(__file__).resolve().parent


def one():
    n = 5000
    i = np.arange(1, n + 1, dtype=np.float64)
    x = np.column_stack(
        (
            np.sin(i / 3) + 0.2 * np.cos(i),
            np.cos(i / 5) + 0.01 * i,
            np.full(n, 2.0),
        )
    )
    result = raftery_diag(as_mcmc(x))
    matrix = np.asarray(result.resmatrix, dtype=np.float64)
    return np.ravel(matrix, order="F").tolist()


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out_path = root / "raftery.diag-py.txt"
out_path.write_text(
    json.dumps({"value": value, "median_ms": statistics.median(elapsed)}) + "\n"
)
