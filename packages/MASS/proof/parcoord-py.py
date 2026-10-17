import statistics
import sys
import time
import types
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
pkg = types.ModuleType("mass")
pkg.__path__ = [str(root / "mass")]
sys.modules["mass"] = pkg
from mass.parcoord import parcoord, parcoord_scale

I = np.arange(1, 13)[:, None]
J = np.arange(1, 5)[None, :]
m = (((I * (J + 3)) % 17) / 3 + J).astype(float)
colnames = ["a", "b", "c", "d"]


def real_call():
    fig, ax = plt.subplots()
    res = parcoord(m, var_label=True, colnames=colnames, ax=ax)
    fig.savefig(root / "docs/output/parcoord-python.svg")
    scaled = res["scaled"]
    value = np.concatenate(
        [scaled.ravel(order="F"), np.asarray(res["xlim"]), np.asarray(res["ylim"])]
    )
    with open(root / "docs/output/parcoord-python-labels.txt", "w") as handle:
        for below, above in zip(res["labels_below"], res["labels_above"]):
            handle.write(f"{below}|{above}\n")
    plt.close(fig)
    return value


value = real_call()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    parcoord_scale(m)
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join("%.17g" % item for item in np.asarray(value, dtype=float).reshape(-1)))
print("%.17g" % statistics.median(elapsed))
