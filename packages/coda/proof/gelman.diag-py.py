import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coda.as_mcmc import as_mcmc
from coda.as_mcmc_list import as_mcmc_list
from coda.gelman_diag import gelman_diag

root = Path(__file__).resolve().parent


def one():
    n = 2000
    i = np.arange(1, n + 1, dtype=np.float64)
    x1 = np.column_stack(
        (np.sin(i / 3) + 0.2 * np.cos(i), np.cos(i / 5) + 0.01 * i)
    )
    x2 = np.column_stack(
        (np.sin(i / 4) + 0.15 * np.cos(i / 2), np.cos(i / 6) + 0.005 * i)
    )
    ml = as_mcmc_list([as_mcmc(x1), as_mcmc(x2)])
    result = gelman_diag(ml, autoburnin=False)
    values = np.ravel(result.psrf, order="F").tolist()
    if result.mpsrf is not None:
        values.append(float(result.mpsrf))
    return values


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out_path = root / "gelman.diag-py.txt"
out_path.write_text(
    json.dumps({"value": value, "median_ms": statistics.median(elapsed)}) + "\n"
)
