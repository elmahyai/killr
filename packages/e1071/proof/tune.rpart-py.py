import json
import statistics
import sys
import time
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [
    str(ROOT / "packages/e1071"),
    str(ROOT / "packages/boot"),
    str(ROOT / "packages/rpart"),
]
if "e1071" not in sys.modules:
    pkg = types.ModuleType("e1071")
    pkg.__path__ = [str(ROOT / "packages/e1071/e1071")]
    sys.modules["e1071"] = pkg

from boot.rng import set_seed  # noqa: E402
from e1071.tune import tune_control  # noqa: E402
from e1071.tune_rpart import tune_rpart  # noqa: E402

X1 = [0.0, 1.2, 2.5, 2.8, 0.1, 2.6, 0.4, 1.9, 2.2, 0.7, 1.5, 2.9]
X2 = [1.0, 0.8, 2.7, 2.4, 0.9, 2.5, 1.6, 0.3, 2.9, 0.2, 1.1, 2.0]
Y = [0.0, 0.0, 1.0, 1.0, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0]
DATA = {"y": Y, "x1": X1, "x2": X2}


def one():
    set_seed(4242)
    res = tune_rpart(
        "y ~ x1 + x2",
        DATA,
        minsplit=[3, 5],
        cp=[0.01, 0.1],
        xval=[0],
        tunecontrol=tune_control(cross=3, performances=True),
    )
    perf = res["performances"]
    return (
        [float(res["best.performance"]), float(res["best.parameters"]["minsplit"]),
         float(res["best.parameters"]["cp"])]
        + [float(row["minsplit"]) for row in perf]
        + [float(row["cp"]) for row in perf]
        + [float(row["error"]) for row in perf]
        + [float(row["dispersion"]) for row in perf]
    )


value = one()
print("tune.rpart best error, best minsplit, best cp, grid minsplit, cp, error, dispersion:")
print(" ".join(f"{v:.6g}" for v in value))
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
(ROOT / "packages/e1071/proof/tune.rpart-py-out.json").write_text(
    json.dumps({"value": value, "median_ms": statistics.median(elapsed)})
)
