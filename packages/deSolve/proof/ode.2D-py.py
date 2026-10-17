import json
import statistics
import sys
import time

import numpy as np

ROOT = "/home/ahmed/killr_projects/killr"
sys.path.insert(0, f"{ROOT}/packages/deSolve")

from types import ModuleType

if "deSolve" not in sys.modules:
    _desolve_pkg = ModuleType("deSolve")
    _desolve_pkg.__path__ = [f"{ROOT}/packages/deSolve/deSolve"]
    sys.modules["deSolve"] = _desolve_pkg


def react2d(t, state, parms):
    nx = parms["nx"]
    ny = parms["ny"]
    nn = nx * ny
    state = np.asarray(state, dtype=np.float64).reshape(-1)
    a = state[:nn]
    b = state[nn : 2 * nn]
    r = parms["r"]
    return [np.concatenate([-r * a, -0.5 * r * b])]


from deSolve.ode2D import ode_2D

nx = 2
ny = 2
nn = nx * ny
parms = {"nx": nx, "ny": ny, "r": 0.7}
state = np.concatenate([np.full(nn, 1.0), np.full(nn, 2.0)])
times = np.arange(0, 1.5, 0.5)


def one():
    out = ode_2D(
        y=state,
        times=times,
        func=react2d,
        parms=parms,
        nspec=2,
        dimens=[nx, ny],
        names=["A", "B"],
        method="lsodes",
        rtol=1e-8,
        atol=1e-8,
        lrw=300,
    )
    return np.ravel(out.data, order="F")


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(
    json.dumps(
        {
            "value": [float(item) for item in value],
            "median_ms": statistics.median(elapsed),
        }
    )
)
