import statistics
import importlib.util
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
spec = importlib.util.spec_from_file_location("mass.errors", root / "mass/errors.py")
errors = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules["mass.errors"] = errors
spec.loader.exec_module(errors)
from mass.truehist import truehist


def one():
    fig, ax = plt.subplots()
    result = truehist(
        [1, 2, 2, 3, 8, 9, 9, 10],
        breaks=[0, 4, 8, 12],
        ax=ax,
    )
    fig.savefig(root / "docs/output/truehist-python.svg")
    value = np.r_[result["breaks"], result["est"]]
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
