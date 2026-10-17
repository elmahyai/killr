import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coda.as_mcmc import as_mcmc
from coda.as_mcmc_list import as_mcmc_list
from coda.chanames import chanames

root = Path(__file__).resolve().parent


def encode_names(names):
    if names is None:
        return [0.0]
    out = [float(len(names))]
    lengths = [float(len(name)) for name in names]
    out.extend(lengths)
    for name in names:
        out.extend(float(ord(char)) for char in name)
    return out


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
    m = as_mcmc(x)
    y = np.column_stack(
        (
            np.sin(i / 4) + 0.15 * np.cos(i / 2),
            np.cos(i / 6) + 0.005 * i,
            np.full(n, 1.0),
        )
    )
    m2 = as_mcmc(y)
    ml = as_mcmc_list([m, m2])
    ml.chain_names = ["chainA", "chainB"]
    ml2 = as_mcmc_list([m, m2])
    ml3 = as_mcmc_list([m, m2, m])
    out = []
    out.extend(encode_names(chanames(ml)))
    out.extend(encode_names(chanames(ml2)))
    out.extend(encode_names(chanames(ml2, allow_null=False)))
    out.extend(encode_names(chanames(ml3, allow_null=False)))
    out.extend(encode_names(chanames(m)))
    out.extend(encode_names(chanames(i)))
    return out


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out_path = root / "chanames-py.txt"
out_path.write_text(
    json.dumps({"value": value, "median_ms": statistics.median(elapsed)}) + "\n"
)
