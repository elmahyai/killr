import json
import statistics
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

ROOT = Path("/home/ahmed/killr_projects/killr")
sys.path[:0] = [str(ROOT / "packages/deSolve"), str(ROOT / "crates/dvode")]

from types import ModuleType

if "deSolve" not in sys.modules:
    _pkg = ModuleType("deSolve")
    _pkg.__path__ = [str(ROOT / "packages/deSolve/deSolve")]
    sys.modules["deSolve"] = _pkg

from deSolve.matplot_0D import matplot_0D  # noqa: E402
from deSolve.vode import vode  # noqa: E402


def logist(t, x, parms):
    r = parms["r"]
    k = parms["K"]
    return [[r * x[0] * (1.0 - x[0] / k)]]


def one():
    out = vode({"N": 0.1}, list(range(0, 11, 2)), logist, {"r": 0.5, "K": 100})
    import matplotlib.pyplot as plt

    res = matplot_0D(out)
    usr = res["usr"]
    plt.close(res["figure"])
    series = out.data[:, 1].reshape(-1)
    return usr + [float(v) for v in series]


OUT = ROOT / "packages/deSolve/docs/output"
OUT.mkdir(parents=True, exist_ok=True)
out = vode({"N": 0.1}, list(range(0, 11, 2)), logist, {"r": 0.5, "K": 100})
import matplotlib.pyplot as plt

matplot_0D(out, _savefig=str(OUT / "matplot.0D-python.svg"))
plt.close("all")

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000.0)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
