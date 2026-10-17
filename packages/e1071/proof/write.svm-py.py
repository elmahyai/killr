import importlib.util
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(ROOT),
    str(ROOT.parents[1] / "crates" / "svm"),
    str(ROOT.parents[1] / "crates" / "svmwrite"),
]

from boot.rng import set_seed
from e1071.svm import svm

_spec = importlib.util.spec_from_file_location(
    "write_svm",
    ROOT / "e1071" / "write_svm.py",
)
_mod = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _mod
_spec.loader.exec_module(_mod)
write_svm = _mod.write_svm


def one():
    set_seed(4242)
    x = [
        [0.0, 1.0],
        [1.2, 0.8],
        [2.5, 2.7],
        [2.8, 2.4],
        [0.1, 0.9],
        [2.6, 2.5],
    ]
    y = ["setosa", "setosa", "versicolor", "versicolor", "setosa", "versicolor"]
    fit = svm(
        x,
        y,
        scale=True,
        kernel="radial",
        cost=1,
        gamma=0.5,
        probability=False,
        cross=0,
    )
    svm_path = Path(tempfile.mkstemp(suffix=".svm")[1])
    scale_path = Path(tempfile.mkstemp(suffix=".scale")[1])
    write_svm(fit, svm_file=str(svm_path), scale_file=str(scale_path))
    return "\n---\n".join(
        [
            svm_path.read_text(encoding="utf-8").rstrip("\n"),
            scale_path.read_text(encoding="utf-8").rstrip("\n"),
        ]
    )


text = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"text": text, "median_ms": statistics.median(elapsed)}))
