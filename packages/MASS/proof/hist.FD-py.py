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
from mass.hist_fd import hist_fd

i = np.arange(1, 61)
x = ((i * 37) % 53) / 7 + 0.25 * ((i * 11) % 5)


def real_call():
    fig, ax = plt.subplots()
    h = hist_fd(x, xlab="x", ax=ax)
    fig.savefig(root / "docs/output/hist.FD-python.svg")
    value = np.concatenate(
        [
            h["breaks"],
            h["counts"].astype(float),
            h["density"],
            h["mids"],
            np.asarray(h["xlim"]),
            np.asarray(h["ylim"]),
        ]
    )
    plt.close(fig)
    return value


value = real_call()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    hist_fd(x, plot=False)
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join("%.17g" % item for item in np.asarray(value, dtype=float).reshape(-1)))
print("%.17g" % statistics.median(elapsed))
