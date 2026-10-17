import json
import statistics
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coda.HPDinterval import HPDinterval

root = Path(__file__).resolve().parent
chains_raw = json.loads((root / "line-chains.json").read_text())
chains = []
for entry in chains_raw:
    matrix = np.array(entry["data"], dtype=np.float64).reshape(
        -1, len(entry["cols"]), order="F"
    )
    wrapped = SimpleNamespace(data=matrix, colnames=entry["cols"])
    chains.append(wrapped)


def one():
    result = HPDinterval(chains)
    values = []
    for item in result:
        values.extend(float(x) for x in item.lower)
        values.extend(float(x) for x in item.upper)
        values.append(float(item.probability))
    return values


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
