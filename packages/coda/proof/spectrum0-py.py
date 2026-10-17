import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coda.spectrum0 import spectrum0

root = Path(__file__).resolve().parent
input_path = root / "spectrum0-input.tsv"


def one():
    x = np.loadtxt(input_path)
    return [float(value) for value in spectrum0(x).spec]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out_path = root / "spectrum0-py.txt"
out_path.write_text(
    json.dumps({"value": value, "median_ms": statistics.median(elapsed)}) + "\n"
)
