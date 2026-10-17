import json
import statistics
import sys
import time
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")

ROOT = Path("/home/ahmed/killr_projects/killr")
sys.path[:0] = [str(ROOT / "packages/deSolve"), str(ROOT / "crates/dvode")]

from types import ModuleType

if "deSolve" not in sys.modules:
    _pkg = ModuleType("deSolve")
    _pkg.__path__ = [str(ROOT / "packages/deSolve/deSolve")]
    sys.modules["deSolve"] = _pkg

from deSolve.matplot_1D import matplot_1D  # noqa: E402
from deSolve.ode1D import ode_1D  # noqa: E402


def O2BOD(t, state, pars):
    n = len(state) // 2
    bod = np.asarray(state[:n])
    o2 = np.asarray(state[n:])
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


def build_out():
    dx = 100.0
    n = 4
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
    times = np.arange(0, 1.5, 0.5)
    return ode_1D(
        y=state,
        times=times,
        func=O2BOD,
        parms=parms,
        nspec=2,
        names=["BOD", "O2"],
        method="vode",
    )


def one():
    out = build_out()
    import matplotlib.pyplot as plt

    res = matplot_1D(out, which=1, ask=False)
    usr = res["usr"]
    plt.close(res["figure"])
    block = out.data[:, 1:5].T.reshape(-1, order="F")
    return [float(v) for v in usr] + [float(v) for v in block]


OUT = ROOT / "packages/deSolve/docs/output"
OUT.mkdir(parents=True, exist_ok=True)
out = build_out()
import matplotlib.pyplot as plt

matplot_1D(out, which=1, ask=False, _savefig=str(OUT / "matplot.1D-python.svg"))
plt.close("all")

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000.0)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
