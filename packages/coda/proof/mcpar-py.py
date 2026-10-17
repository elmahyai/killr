import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coda.as_mcmc import mcmc
from coda.mcpar import mcpar

root = Path(__file__).resolve().parent


def one():
    first = mcmc(np.arange(1, 9), start=11, end=25, thin=2)
    second = mcmc(np.arange(1, 13).reshape((6, 2), order="F"), start=11, end=16, thin=1)
    return np.concatenate((mcpar(first), mcpar(second)))


value = one().tolist()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out = json.dumps(
    {"value": value, "median_ms": statistics.median(elapsed)},
    separators=(",", ":"),
) + "\n"
(root / "mcpar-py.txt").write_text(out)
output = root.parent / "docs" / "output" / "mcpar-python.txt"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(out)
