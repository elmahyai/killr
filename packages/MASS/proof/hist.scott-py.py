import importlib.util
import statistics
import sys
import time
import types
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
_pkg = _root / "mass"
sys.path.insert(0, str(_root))
if "mass" not in sys.modules:
    mass = types.ModuleType("mass")
    mass.__path__ = [str(_pkg)]
    sys.modules["mass"] = mass
if "mass.errors" not in sys.modules:
    _spec = importlib.util.spec_from_file_location("mass.errors", _pkg / "errors.py")
    _mod = importlib.util.module_from_spec(_spec)
    assert _spec is not None and _spec.loader is not None
    sys.modules["mass.errors"] = _mod
    _spec.loader.exec_module(_mod)
_spec = importlib.util.spec_from_file_location("mass.hist_scott", _pkg / "hist_scott.py")
_hist = importlib.util.module_from_spec(_spec)
assert _spec is not None and _spec.loader is not None
sys.modules["mass.hist_scott"] = _hist
_spec.loader.exec_module(_hist)
hist_scott = _hist.hist_scott

import numpy as np


def one():
    h = hist_scott([1, 2, 2, 3, 8, 9, 9, 10], plot=False)
    return np.concatenate([h["breaks"], h["counts"], h["density"]])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
flat = np.asarray(value, dtype=float).reshape(-1)
print("\n".join("%.17g" % item for item in flat))
print("%.17g" % statistics.median(elapsed))
