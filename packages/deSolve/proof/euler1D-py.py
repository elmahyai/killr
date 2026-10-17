import json
import statistics
import sys
import time
from types import ModuleType

import numpy as np

ROOT = "/home/ahmed/killr_projects/killr"
sys.path.insert(0, f"{ROOT}/packages/deSolve")

if "deSolve" not in sys.modules:
    _desolve_pkg = ModuleType("deSolve")
    _desolve_pkg.__path__ = [f"{ROOT}/packages/deSolve/deSolve"]
    sys.modules["deSolve"] = _desolve_pkg

from deSolve.euler1D import euler_1D


def O2BOD(t, state, pars):
    n = len(state) // 2
    bod = np.asarray(state[:n], dtype=np.float64)
    o2 = np.asarray(state[n:], dtype=np.float64)
    dx = pars["dx"]
    v = pars["v"]
    r = pars["r"]
    p = pars["p"]
    o2sat = pars["O2sat"]
    bod_0 = pars["BOD_0"]
    o2_0 = pars["O2_0"]
    flux_bod = v * np.concatenate([[bod_0], bod])
    flux_o2 = v * np.concatenate([[o2_0], o2])
    bodrate = r * bod
    dbod = -np.diff(flux_bod) / dx - bodrate
    do2 = -np.diff(flux_o2) / dx - bodrate + p * (o2sat - o2)
    return [np.concatenate([dbod, do2])]


dx = 100.0
n = len(np.arange(dx / 2, 400 + dx / 2, dx))
parms = {
    "dx": dx,
    "v": 1e3,
    "r": 0.05,
    "p": 0.5,
    "O2sat": 300.0,
    "BOD_0": 1000.0,
    "O2_0": 200.0,
}
state = np.concatenate([np.full(n, 200.0), np.full(n, 200.0)])
times = np.arange(0, 1.25, 0.25)


def one():
    out = euler_1D(
        y=state,
        times=times,
        func=O2BOD,
        parms=parms,
        nspec=2,
        names=["BOD", "O2"],
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
