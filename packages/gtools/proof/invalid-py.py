import importlib.util
import statistics
import sys
import time
import types

import numpy as np

_PKG = "/home/ahmed/killr_projects/killr/packages/gtools/gtools"


def _load_module(name: str, filename: str):
    if "gtools" not in sys.modules:
        sys.modules["gtools"] = types.ModuleType("gtools")
    path = f"{_PKG}/{filename}"
    spec = importlib.util.spec_from_file_location(f"gtools.{name}", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[f"gtools.{name}"] = mod
    spec.loader.exec_module(mod)
    return mod


_load_module("na_replace", "na_replace.py")
_invalid_mod = _load_module("invalid", "invalid.py")
invalid = _invalid_mod.invalid
TryError = _invalid_mod.TryError


def fmt(v: bool) -> str:
    return "TRUE" if v else "FALSE"


def one() -> str:
    failed = TryError("non-numeric argument to mathematical function")
    parts = [
        fmt(invalid(None)),
        fmt(invalid(42)),
        fmt(invalid(np.array([], dtype=np.float64))),
        fmt(invalid(np.nan)),
        fmt(invalid(failed)),
    ]
    return "|".join(parts)


invalid(None)
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value)
print("MS")
print(f"{statistics.median(elapsed):.17g}")
