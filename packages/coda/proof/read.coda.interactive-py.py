import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coda.read_coda import read_coda
from coda.mcmc_list import mcmc_list
from coda.varnames import varnames
from coda.nchain import nchain

root = Path(__file__).resolve().parent
outfile = root / "read.coda-proof.out"
indexfile = root / "read.coda-proof.ind"


def one():
    # Simulate what read.coda.interactive would do:
    # It prompts for files and reads them into an mcmc.list
    chains = []
    chains.append(read_coda(outfile, indexfile, quiet=True))
    chains.append(read_coda(outfile, indexfile, quiet=True))
    
    obj = mcmc_list(*chains)
    
    # Build result similar to R: nchains, then for each chain all data + mcpar
    parts = [float(nchain(obj))]
    for chain in obj.chains:
        array = np.asarray(chain.data, dtype=np.float64)
        parts.extend(np.ravel(array, order="F").tolist())
        parts.extend(chain.mcpar.tolist())
    
    # Add name indices
    names = varnames(obj, allow_null=False)
    for name in ["alpha", "beta"]:
        try:
            parts.append(float(names.index(name) + 1))
        except ValueError:
            pass
    
    return parts


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out_path = root / "read.coda.interactive-py.txt"
out_path.write_text(
    json.dumps({"value": value, "median_ms": statistics.median(elapsed)}) + "\n"
)
