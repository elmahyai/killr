import json
import sys
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
    chains.append(SimpleNamespace(data=matrix, colnames=entry["cols"]))

result = HPDinterval(chains)
labels = ("line1", "line2")
for label, item in zip(labels, result):
    print(f"${label}")
    names = item.rownames if item.rownames is not None else range(1, len(item.lower) + 1)
    print(f"         lower   upper")
    for name, lo, hi in zip(names, item.lower, item.upper):
        print(f"{name} {lo:8.5f} {hi:8.5f}")
    print(f'attr(,"Probability")')
    print(f"[1] {item.probability}")
