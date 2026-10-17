import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coda.as_mcmc import as_mcmc
from coda.as_mcmc_list import as_mcmc_list
from coda.is_mcmc_list import is_mcmc_list

root = Path(__file__).resolve().parent


def one():
    n = 2000
    i = np.arange(1, n + 1, dtype=np.float64)
    x = np.column_stack(
        (
            np.sin(i / 3) + 0.2 * np.cos(i),
            np.cos(i / 5) + 0.01 * i,
            np.full(n, 2.0),
        )
    )
    y = np.column_stack(
        (
            np.sin(i / 4) + 0.15 * np.cos(i / 2),
            np.cos(i / 6) + 0.005 * i,
            np.full(n, 1.0),
        )
    )
    chain = as_mcmc(x)
    flags = [
        is_mcmc_list(as_mcmc_list([chain, as_mcmc(y)])),
        is_mcmc_list(chain),
        is_mcmc_list([chain]),
        is_mcmc_list(None),
    ]
    return [1.0 if flag else 0.0 for flag in flags]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out_path = root / "is.mcmc.list-py.txt"
out_path.write_text(
    json.dumps({"value": value, "median_ms": statistics.median(elapsed)}) + "\n"
)
docs = root.parent / "docs" / "output" / "is.mcmc.list-python.txt"
docs.write_text(" ".join("TRUE" if flag == 1.0 else "FALSE" for flag in value) + "\n")
