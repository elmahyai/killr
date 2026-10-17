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


def react3d(t, state, parms):
    state = np.asarray(state, dtype=np.float64).reshape(-1)
    r = parms["r"]
    return [-r * state]


from deSolve.ode3D import ode_3D

dims = [2, 2, 2]
state = np.full(8, 1.0)
times = np.arange(0, 1.5, 0.5)
parms = {"r": 0.5}


def one():
    out = ode_3D(
        y=state,
        times=times,
        func=react3d,
        parms=parms,
        nspec=1,
        dimens=dims,
        method="lsodes",
        rtol=1e-8,
        atol=1e-8,
        lrw=800,
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
