import importlib.util
import statistics
import sys
import time
import types
from pathlib import Path

import numpy as np

_root = Path(__file__).resolve().parents[1]
_pkg = _root / "mass"
sys.path.insert(0, str(_root))
if "mass" not in sys.modules:
    mass = types.ModuleType("mass")
    mass.__path__ = [str(_pkg)]
    sys.modules["mass"] = mass


def _load(name: str, filename: str):
    key = f"mass.{name}"
    if key in sys.modules:
        return sys.modules[key]
    spec = importlib.util.spec_from_file_location(key, _pkg / filename)
    mod = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[key] = mod
    spec.loader.exec_module(mod)
    return mod


_errors = _load("errors", "errors.py")
_loglm = _load("loglm", "loglm.py")
_loglm1 = _load("loglm1", "loglm1.py")
_FreqArray = _loglm._FreqArray
_build_terms = _loglm._build_terms
loglm1 = _loglm1.loglm1


def one():
    data = np.array([[10.0, 20.0], [30.0, 40.0]])
    freq = data.view(_FreqArray)
    freq._dimnames = ["A", "B"]
    formula = "~ A + B"
    freq.terms = _build_terms(formula, freq._dimnames, denumerate=True)
    fm = loglm1(formula, freq)
    return np.array([fm.lrt, fm.pearson, fm.df, float(fm.nobs)])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for item in value:
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
