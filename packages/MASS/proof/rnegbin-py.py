import importlib.util
import statistics
import sys
import time
import types
from pathlib import Path

import numpy as np

_root = Path(__file__).resolve().parents[1]
_repo = _root.parent
sys.path.insert(0, str(_repo / "boot"))
sys.path.insert(0, str(_repo / "extraDistr"))

from boot.rng import set_seed

if "mass" not in sys.modules:
    _mass = types.ModuleType("mass")
    _mass.__path__ = [str(_root / "mass")]
    sys.modules["mass"] = _mass
_err_spec = importlib.util.spec_from_file_location("mass.errors", _root / "mass" / "errors.py")
_errors = importlib.util.module_from_spec(_err_spec)
assert _err_spec is not None and _err_spec.loader is not None
sys.modules["mass.errors"] = _errors
_err_spec.loader.exec_module(_errors)
_rneg_spec = importlib.util.spec_from_file_location("mass.rnegbin", _root / "mass" / "rnegbin.py")
_rneg = importlib.util.module_from_spec(_rneg_spec)
assert _rneg_spec is not None and _rneg_spec.loader is not None
sys.modules["mass.rnegbin"] = _rneg
_rneg_spec.loader.exec_module(_rneg)
rnegbin = _rneg.rnegbin


def one():
    set_seed(42)
    return rnegbin(100, mu=5.5, theta=4.5)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
flat = np.asarray(value, dtype=float).reshape(-1)
print("\n".join("%.17g" % item for item in flat))
print("%.17g" % statistics.median(elapsed))
