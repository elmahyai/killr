import json
import statistics
import sys
import time
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "packages/e1071"), str(ROOT / "packages/boot"), str(ROOT / "packages/proxy")]
if "e1071" not in sys.modules:
    pkg = types.ModuleType("e1071")
    pkg.__path__ = [str(ROOT / "packages/e1071/e1071")]
    sys.modules["e1071"] = pkg

from boot.rng import set_seed  # noqa: E402
from e1071.gknn import predict_gknn  # noqa: E402
from e1071.tune import tune_control  # noqa: E402
from e1071.tune_gknn import best_gknn  # noqa: E402

X = [
    [0.0, 1.0], [1.2, 0.8], [2.5, 2.7], [2.8, 2.4], [0.1, 0.9], [2.6, 2.5],
    [0.4, 1.6], [1.9, 0.3], [2.2, 2.9], [0.7, 0.2], [1.5, 1.1], [2.9, 2.0],
]
Y = ["a", "a", "b", "b", "a", "b", "a", "a", "b", "a", "a", "b"]


def one():
    set_seed(4242)
    res = best_gknn(
        X,
        Y,
        k=[1, 3, 5],
        method="Euclidean",
        tunecontrol=tune_control(cross=3),
    )
    levels = list(res["levels"])
    codes = [float(levels.index(v) + 1) for v in predict_gknn(res, X)]
    return codes + [float(res["k"])]


value = one()
print("best.gknn codes on X, best k:")
print(" ".join(f"{v:.6g}" for v in value))
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
(ROOT / "packages/e1071/proof/best.gknn-py-out.json").write_text(
    json.dumps({"value": value, "median_ms": statistics.median(elapsed)})
)
