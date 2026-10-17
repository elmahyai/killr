import json
import statistics
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coda.as_array_mcmc_list import as_array_mcmc_list

root = Path(__file__).resolve().parent
chains_raw = json.loads((root / "line-chains.json").read_text())
chains = []
for entry in chains_raw:
    matrix = np.array(entry["data"], dtype=np.float64).reshape(
        -1, len(entry["cols"]), order="F"
    )
    chains.append(SimpleNamespace(data=matrix, colnames=entry["cols"]))


def one():
    array = as_array_mcmc_list(chains, drop=True)
    return np.ravel(np.asarray(array, dtype=np.float64), order="F")


value = one().tolist()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out_path = root / "as.array.mcmc.list-py.txt"
out_path.write_text(
    json.dumps({"value": value, "median_ms": statistics.median(elapsed)}) + "\n"
)
