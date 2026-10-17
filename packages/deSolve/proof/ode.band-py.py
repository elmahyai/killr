import json
import statistics
import sys
import time

import numpy as np

ROOT = "/home/ahmed/killr_projects/killr"
sys.path[:0] = [f"{ROOT}/packages/deSolve", f"{ROOT}/crates/dvode"]

from types import ModuleType

if "deSolve" not in sys.modules:
    _desolve_pkg = ModuleType("deSolve")
    _desolve_pkg.__path__ = [f"{ROOT}/packages/deSolve/deSolve"]
    sys.modules["deSolve"] = _desolve_pkg


def chain(t, y, parms):
    k = parms["k"]
    y = np.asarray(y, dtype=np.float64).reshape(-1)
    return [-k * y]


from deSolve.odeband import ode_band

y = np.full(5, 1.0)
times = np.arange(0, 2.5, 0.5)
parms = {"k": 0.3}


def one():
    out = ode_band(
        y=y,
        times=times,
        func=chain,
        parms=parms,
        nspec=1,
        dimens=5,
        bandup=1,
        banddown=1,
        method="vode",
        rtol=1e-8,
        atol=1e-8,
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
