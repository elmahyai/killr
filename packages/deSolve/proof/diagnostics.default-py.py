import importlib.util
import statistics
import sys
import time
import types
import warnings
from pathlib import Path

import numpy as np

ROOT = Path("/home/ahmed/killr_projects/killr")
PKG = ROOT / "packages/deSolve/deSolve"
sys.path.insert(0, str(ROOT / "packages/deSolve"))


def _ensure_desolve_package() -> None:
    if "deSolve" not in sys.modules:
        pkg = types.ModuleType("deSolve")
        pkg.__path__ = [str(PKG)]
        pkg.__package__ = "deSolve"
        sys.modules["deSolve"] = pkg


def _load(stem: str):
    _ensure_desolve_package()
    name = f"deSolve.{stem}"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(
        name, PKG / f"{stem}.py", submodule_search_locations=[str(PKG)]
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_load("timestep")
_load("rk4")
diagnostics_default = _load("diagnostics_default").diagnostics_default


def one() -> str:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        diagnostics_default(np.array([1, 2, 3], dtype=np.int32))
    return str(caught[0].message)


invisible = one()
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value)
print("MS")
print(f"{statistics.median(elapsed):.17g}")
