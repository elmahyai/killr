import importlib.util
import io
import statistics
import sys
import time
import types
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


def _captured_text(buffer: io.StringIO) -> str:
    text = buffer.getvalue()
    if text.endswith("\n"):
        text = text[:-1]
    return text


_load("timestep")
rk4 = _load("rk4")
diagnostics_deSolve = _load("diagnostics_deSolve").diagnostics_deSolve
DeSolveMatrix = rk4.DeSolveMatrix


def _lsode_like_object():
    istate = [None] * 21
    for index, value in [(0, 2), (1, 52), (2, 69), (4, 5), (5, 5), (6, 0), (7, 32), (8, 21), (13, 5)]:
        istate[index] = value
    obj = DeSolveMatrix(np.zeros((1, 2)), ["time", "N"], istate, None, None, None)
    obj.type = "lsode"
    obj.rstate = [0.2695228, 0.2695228, 10.23201, 0, None]
    return obj


def one() -> str:
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        diagnostics_deSolve(_lsode_like_object())
    finally:
        sys.stdout = old
    return _captured_text(buf)


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
