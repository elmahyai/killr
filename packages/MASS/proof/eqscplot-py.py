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
from mass.eqscplot import eqscplot


def one():
    fig, ax = plt.subplots()
    eqscplot(np.column_stack(([-2, 0, 3], [-2, 3, 1])), xlab="X", ylab="Y", ax=ax)
    fig.savefig(root / "docs/output/eqscplot-python.svg")
    value = np.asarray(ax.axis())[2:4]
    plt.close(fig)
    return value


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join("%.17g" % item for item in value))
print("%.17g" % statistics.median(elapsed))
