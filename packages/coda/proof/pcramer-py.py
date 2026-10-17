import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coda.pcramer import pcramer

root = Path(__file__).resolve().parent

quantiles = np.array(
    [1e-4, 0.005, 0.00543, 0.01, 0.05, 0.1, 0.461, 1.0, 2.0, 10.0, 100.0],
    dtype=np.float64,
)


def one():
    default = np.asarray(pcramer(quantiles), dtype=np.float64)
    tighter = np.asarray(pcramer(quantiles, eps=1e-8), dtype=np.float64)
    return np.concatenate((default, tighter)).tolist()


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out_path = root / "pcramer-py.txt"
out_path.write_text(
    json.dumps({"value": value, "median_ms": statistics.median(elapsed)}) + "\n"
)
shown = " ".join(format(float(item), ".17g") for item in value)
docs = root.parent / "docs" / "output" / "pcramer-python.txt"
docs.write_text(shown + "\n")
