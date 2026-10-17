import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coda.as_mcmc import as_mcmc
from coda.as_mcmc_list import as_mcmc_list
from coda.varnames import varnames

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
    m.colnames = ["alpha", "beta", "gamma"]
    y = np.column_stack(
        (
            np.sin(i / 4) + 0.15 * np.cos(i / 2),
            np.cos(i / 6) + 0.005 * i,
            np.full(n, 1.0),
        )
    )
    m2 = as_mcmc(y)
    ml = as_mcmc_list([m, m])
    z = np.column_stack((np.sin(i / 7), np.cos(i / 8)))
    mu = as_mcmc(z)
    v = np.sin(i / 9)
    mv = as_mcmc(v)
    out = []
    for args in (
        (m,),
        (mu, False),
        (mv,),
        (mv, False),
        (ml,),
        (ml, False),
        (m2,),
        (m2, False),
        (i,),
    ):
        if len(args) == 1:
            out.extend(encode_names(varnames(args[0])))
        else:
            out.extend(encode_names(varnames(args[0], allow_null=args[1])))
    return out


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out_path = root / "varnames-py.txt"
out_path.write_text(
    json.dumps({"value": value, "median_ms": statistics.median(elapsed)}) + "\n"
)
