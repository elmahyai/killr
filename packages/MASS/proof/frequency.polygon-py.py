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
from mass.frequency_polygon import frequency_polygon, frequency_polygon_data

i = np.arange(1, 61)
x = ((i * 37) % 53) / 7 + 0.25 * ((i * 11) % 5)


def real_call():
    fig, ax = plt.subplots()
    res = frequency_polygon(x, xlab="x", ylab="Frequency", ax=ax)
    fig.savefig(root / "docs/output/frequency.polygon-python.svg")
    value = np.concatenate([res["midpoints"], res["counts"], np.asarray(res["xlim"]), np.asarray(res["ylim"])])
    plt.close(fig)
    return value


value = real_call()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    frequency_polygon_data(x)
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join("%.17g" % item for item in np.asarray(value, dtype=float).reshape(-1)))
print("%.17g" % statistics.median(elapsed))
