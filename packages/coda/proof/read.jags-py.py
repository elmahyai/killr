import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coda.read_jags import read_jags
from coda.varnames import varnames

root = Path(__file__).resolve().parent
outfile = root / "CODAchain.out"


def one():
    obj = read_jags(outfile, quiet=True)
    array = np.asarray(obj.data, dtype=np.float64)
    vals = np.ravel(array, order="F").tolist()
    mcpar = obj.mcpar.tolist()
    names = varnames(obj, allow_null=False)
    name_part = [float(names.index(name) + 1) for name in ("alpha", "beta")]
    return vals + mcpar + name_part


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out_path = root / "read.jags-py.txt"
out_path.write_text(
    json.dumps({"value": value, "median_ms": statistics.median(elapsed)}) + "\n"
)
