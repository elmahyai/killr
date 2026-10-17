import importlib.util
import json
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_root))
if "mass" not in sys.modules:
    import types

    _mass = types.ModuleType("mass")
    _mass.__path__ = [str(_root / "mass")]
    sys.modules["mass"] = _mass
if "mass.errors" not in sys.modules:
    _err_spec = importlib.util.spec_from_file_location(
        "mass.errors", _root / "mass" / "errors.py"
    )
    _errors = importlib.util.module_from_spec(_err_spec)
    assert _err_spec is not None and _err_spec.loader is not None
    sys.modules["mass.errors"] = _errors
    _err_spec.loader.exec_module(_errors)

_MODULE = _root / "mass" / "rms_curv.py"
_SPEC = importlib.util.spec_from_file_location("rms_curv", _MODULE)
assert _SPEC is not None and _SPEC.loader is not None
_rms_curv_mod = importlib.util.module_from_spec(_SPEC)
sys.modules["rms_curv"] = _rms_curv_mod
_SPEC.loader.exec_module(_rms_curv_mod)
rms_curv = _rms_curv_mod.rms_curv

_CASE = json.loads(
    Path(__file__).with_name("rms.curv-purfit1.json").read_text(encoding="utf-8")
)


@dataclass
class _FittedValues:
    gradient: np.ndarray
    hessian: np.ndarray


@dataclass
class _NlsModel:
    values: _FittedValues

    def fitted(self):
        return self.values


@dataclass
class _NlsFit:
    m: _NlsModel
    deviance: float


def _purfit1() -> _NlsFit:
    gradient = np.asarray(_CASE["gradient"], dtype=float)
    hess_slices = [np.asarray(item, dtype=float) for item in _CASE["hessian"]]
    n, p = gradient.shape
    hessian = np.stack(hess_slices, axis=2)
    if hessian.shape != (n, p, len(hess_slices)):
        raise ValueError("hessian shape mismatch")
    return _NlsFit(
        m=_NlsModel(_FittedValues(gradient=gradient, hessian=hessian)),
        deviance=float(_CASE["deviance"]),
    )


def one():
    result = rms_curv(_purfit1())
    return np.concatenate(
        [
            np.array([result.pe, result.ic, result.ct, result.ci], dtype=float),
            np.asarray(result.C, dtype=float).reshape(-1, order="F"),
        ]
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
flat = np.asarray(value, dtype=float).reshape(-1)
print("\n".join("%.17g" % item for item in flat))
print("%.17g" % statistics.median(elapsed))
