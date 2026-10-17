import json
import os
import statistics
import sys
import time
import types
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "packages/e1071")]
if "e1071" not in sys.modules:
    pkg = types.ModuleType("e1071")
    pkg.__path__ = [str(ROOT / "packages/e1071/e1071")]
    sys.modules["e1071"] = pkg

from e1071.probplot import probplot  # noqa: E402

X = [0.3, -1.2, 2.5, 0.8, -0.4, 1.9, 0.1, -2.2, 3.1, 0.6, -0.9, 1.4]


def one():
    z = probplot(X, line=True)
    values = [z["int"], z["slope"]] + [float(v) for v in z["qdist"]([0.01, 0.5, 0.99])]
    plt.close(z["figure"])
    return values


value = one()
print("probplot int, slope, qdist at 0.01, 0.5, 0.99:")
print(" ".join(f"{v:.6g}" for v in value))
z = probplot(X, line=True)
z["figure"].savefig(ROOT / "packages/e1071/docs/output/probplot-python.svg")
plt.close(z["figure"])
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
(ROOT / "packages/e1071/proof/probplot-py-out.json").write_text(
    json.dumps({"value": value, "median_ms": statistics.median(elapsed)})
)
