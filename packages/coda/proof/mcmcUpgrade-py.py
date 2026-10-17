import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coda.as_mcmc import Mcmc
from coda.mcmc_upgrade import mcmc_upgrade

root = Path(__file__).resolve().parent


def one():
    mat1 = np.array(
        [
            [0.11, 1.11],
            [0.22, 1.22],
            [0.33, 1.33],
            [0.44, 1.44],
            [0.55, 1.55],
            [0.66, 1.66],
        ],
        dtype=np.float64,
    )
    mat2 = mat1 + 10.0
    arr = np.empty((6, 2, 2), dtype=np.float64)
    arr[:, :, 0] = mat1
    arr[:, :, 1] = mat2
    obj = Mcmc(data=arr, tspar=np.array([1.0, 6.0, 1.0], dtype=np.float64))
    upgraded = mcmc_upgrade(obj)
    if hasattr(upgraded, "chains"):
        chains = upgraded.chains
        parts = [float(len(chains))]
    else:
        chains = [upgraded]
        parts = [1.0]
    for chain in chains:
        array = np.asarray(chain.data, dtype=np.float64)
        parts.extend(np.ravel(array, order="F").tolist())
        parts.extend(chain.mcpar.tolist())
    return parts


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out_path = root / "mcmcUpgrade-py.txt"
out_path.write_text(
    json.dumps({"value": value, "median_ms": statistics.median(elapsed)}) + "\n"
)
