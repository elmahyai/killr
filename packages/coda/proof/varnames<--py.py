import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coda.mcmc import mcmc
from coda.mcmc_list import mcmc_list
from coda.varnames import varnames
from coda.varnames_setter import set_varnames


def encode_names(v):
    """Encode names similar to R proof."""
    if v is None:
        return [0]
    if isinstance(v, str):
        v = [v]
    
    out = [len(v)]
    out.extend([len(name) for name in v])
    for name in v:
        for char in name:
            out.append(ord(char))
    return out


def one():
    n = 2000
    i = np.arange(1, n + 1)
    x = np.column_stack([
        np.sin(i / 3) + 0.2 * np.cos(i),
        np.cos(i / 5) + 0.01 * i,
        np.full(n, 2.0)
    ])
    m = mcmc(x)
    
    # Test varnames<- assignment on single mcmc object
    set_varnames(m, ["theta1", "theta2", "theta3"])
    names_after_set = varnames(m)
    
    # Create mcmc.list with compatible chains
    y = np.column_stack([
        np.sin(i / 4) + 0.15 * np.cos(i / 2),
        np.cos(i / 6) + 0.005 * i,
        np.full(n, 1.0)
    ])
    m2 = mcmc(y)
    
    # Set names on m2 to match m before creating list
    set_varnames(m2, ["theta1", "theta2", "theta3"])
    ml = mcmc_list(m, m2)
    
    # Now test varnames<- on the mcmc.list
    set_varnames(ml, ["alpha", "beta", "gamma"])
    names_list = varnames(ml)
    
    result = []
    result.extend(encode_names(names_after_set))
    result.extend(encode_names(names_list))
    result.extend(encode_names(varnames(ml.chains[0])))
    result.extend(encode_names(varnames(ml.chains[1])))
    
    return result


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out_path = Path(__file__).resolve().parent / "varnames<--py.txt"
out_path.write_text(
    json.dumps({"value": value, "median_ms": statistics.median(elapsed)}) + "\n"
)
