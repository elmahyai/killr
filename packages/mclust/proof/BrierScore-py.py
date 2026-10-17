import importlib.util
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
_module_path = Path(__file__).resolve().parent.parent / "mclust" / "brier_score.py"
_spec = importlib.util.spec_from_file_location("brier_score", _module_path)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
BrierScore = _mod.BrierScore


def one():
    z = np.array([[0.7, 0.3], [0.2, 0.8], [0.6, 0.4]], dtype=float)
    class_ = np.array([1, 2, 1], dtype=int)
    return BrierScore(z, class_)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("%.17g" % value)
print("%.17g" % statistics.median(elapsed))
