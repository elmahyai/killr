import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coda.as_mcmc import Mcmc
from coda.as_mcmc_list import McmcList, as_mcmc_list

root = Path(__file__).resolve().parent
chains_raw = json.loads((root / "line-chains.json").read_text())
chains = []
for entry in chains_raw:
    matrix = np.array(entry["data"], dtype=np.float64).reshape(
        -1, len(entry["cols"]), order="F"
    )
    chain = Mcmc(data=matrix, start=1.0, end=200.0, thin=1.0)
    chain.colnames = list(entry["cols"])
    chains.append(chain)
line = McmcList(chains=chains)


def one():
    obj = as_mcmc_list(line)
    parts = [len(obj.chains)]
    for chain in obj.chains:
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

out_path = root / "as.mcmc.list-py.txt"
out_path.write_text(
    json.dumps({"value": value, "median_ms": statistics.median(elapsed)}) + "\n"
)
