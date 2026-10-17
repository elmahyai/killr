import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coda.bugs2jags import _load_dump, bugs2jags

root = Path(__file__).resolve().parent
infile = root / "bugs2jags-in.dat"
outfile = root / "bugs2jags-out-py.dat"

if not infile.exists():
    text = (
        "list(N = 5L, y = c(1.1, 2.2, 3.3, 4.4, 5.5), "
        "X = structure(1:12, dim = 3:4), Z = structure(1:24, dim = 2:4))"
    )
    infile.write_text(text, encoding="utf-8")


def one():
    bugs2jags(infile, outfile)
    env = _load_dump(outfile)
    y = env["y"]
    if hasattr(y, "values"):
        y = y.values
    x_arr = env["X"]
    z_arr = env["Z"]
    return [
        float(env["N"]),
        float(np.sum(y)),
        float(np.sum(x_arr)),
        float(np.sum(z_arr)),
        float(x_arr[0, 0]),
        float(x_arr[2, 3]),
        float(z_arr[0, 1, 2]),
    ]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out_path = root / "bugs2jags-py.txt"
out_path.write_text(
    json.dumps({"value": value, "median_ms": statistics.median(elapsed)}) + "\n"
)
