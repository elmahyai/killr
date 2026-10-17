import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coda.read_openbugs import read_openbugs

root = Path(__file__).resolve().parent


def one():
    obj = read_openbugs("", quiet=True)
    parts = [float(len(obj.chains))]
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

out_path = root / "read.openbugs-py.txt"
out_path.write_text(
    json.dumps({"value": value, "median_ms": statistics.median(elapsed)}) + "\n"
)
