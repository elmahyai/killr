import importlib.util, math, statistics, sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    import mclust_kernels  # noqa: F401  an installed binding, if present
except ImportError:
    _spec = importlib.util.spec_from_file_location(
        "mclust_kernels", ROOT / "crates" / "mclust" / "target" / "release" / "libmclust_kernels.so")
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    sys.modules["mclust_kernels"] = _mod

from mclust.em_e_eei_eii_evi_v import emV

n, p = 60, 3
x = np.array([[math.sin(.37*i+1.3*j)+.4*math.cos(.11*i*j)+.05*i/n*j for j in range(1, p+1)] for i in range(1, n+1)])
x1 = x[:, 0].copy()
mu1 = np.array([.1, .5])

def pars(pro, Vinv=None):
    q = {"pro": np.asarray(pro, dtype=float), "mean": mu1, "variance": {"sigmasq": np.array([.8, 1.5])}}
    if Vinv is not None:
        q["Vinv"] = Vinv
    return q

def flat(o, keys):
    v = o["parameters"]["variance"]
    f = lambda a: np.asarray(a, dtype=float).ravel(order="F").tolist()
    out = [float(o["returnCode"])] + f(o["parameters"]["pro"]) + f(o["parameters"]["mean"])
    for k in keys:
        out += f(v[k])
    out += f(o["z"])
    if o.get("loglik") is not None:
        out += f(o["loglik"])
    return out

def one():
    return ([float(v) for v in flat(emV(x1, pars([.4, .6])), ["sigmasq"])]
            + [float(v) for v in flat(emV(x1, pars([.3, .45, .25], .15)), ["sigmasq"])])

value = one()
elapsed = []
for _ in range(20):
    t = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - t) * 1000)
for v in value:
    print("%.17g" % v)
print("%.17g" % statistics.median(elapsed))
