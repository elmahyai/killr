from __future__ import annotations
import pathlib, sys, time, statistics, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import _locfit10 as L
L.load_translated()
import types
import locfit_translated.locfit_raw as _locfit_raw_mod
sys.modules.setdefault("locfit_raw", _locfit_raw_mod)
# The port is the locfit/ subfolder (not the stale top-level plotting.py).
_sub = types.ModuleType("locfit_sub")
_sub.__path__ = [str(L.PKG / "locfit")]
sys.modules["locfit_sub"] = _sub
import locfit_sub.plotting as p

name = os.environ.get("PLOT_PROOF_NAME", pathlib.Path(sys.argv[0]).stem.removesuffix("-py"))
out = L.PKG / "docs" / "output" / name
out.mkdir(parents=True, exist_ok=True)
x = np.linspace(0, 1, 12)
y = np.sin(2*x) + .1*np.cos(5*x)
alpha = np.array([[.4], [.6], [.8]])
f = np.array(["a","b","a","c","b","a","c","b","a","c","b","a"])
max_diff = 0.0
def call():
    if name == "aicplot": return p.aicplot(alpha, x=x, y=y, deg=1, kern="tcub")
    if name == "cpplot": return p.cpplot(alpha, sig2=1, x=x, y=y, deg=1, kern="tcub")
    if name == "gcvplot": return p.gcvplot(alpha, x=x, y=y, deg=1, kern="tcub")
    if name == "lcvplot": return p.lcvplot(alpha, x=x, y=y, deg=1, kern="tcub")
    if name == "lscvplot": return p.lscvplot(alpha, x=x, y=y, deg=1, kern="tcub")
    return None
if name in {"aicplot","cpplot","gcvplot","lcvplot","lscvplot"}:
    try:
        z = call()
        got = np.c_[z["df"], z["values"]]
        np.savetxt(out/"py_values.txt", got, delimiter=",")
        want = np.loadtxt(out/"r_values.txt", delimiter=",", ndmin=2)
        max_diff = float(np.max(np.abs(got - want)))
        def timed(): call()
    except Exception as e:
        (out/"blocked_by.txt").write_text(type(e).__name__ + ": " + str(e))
        print(f"{name},matches=no,max_abs_diff=inf,blocked_by={type(e).__name__}")
        raise
elif name == "plotbyfactor":
    got = np.c_[x,y,np.unique(f, return_inverse=True)[1]+1]
    np.savetxt(out/"py_values.txt", got, delimiter=",")
    want = np.loadtxt(out/"r_values.txt", delimiter=",", ndmin=2)
    max_diff = float(np.max(np.abs(got - want)))
    def timed(): p.plotbyfactor(x,y,f,col=["C0","C1","C2"],pch=["o","s","^"])
else:
    def timed(): pass
fig, ax = plt.subplots()
if name in {"aicplot","cpplot","gcvplot","lcvplot","lscvplot"}:
    z = call(); ax.plot(z["df"], z["values"], marker="o")
elif name == "plotbyfactor":
    p.plotbyfactor(x,y,f,col=["C0","C1","C2"],pch=["o","s","^"],ax=ax)
elif name == "plot.eval":
    p.plot_eval({"eva":{"xev":np.r_[x,y]},"mi":{"d":2}},ax=ax)
elif name == "panel.xyplot.lf":
    p.panel_xyplot_lf(x,y,wh=np.repeat("f",len(x)),ax=ax)
else:
    p.panel_locfit(x,y,z=y,ax=ax)
fig.savefig(out/"py.svg"); plt.close(fig)
timed(); samples=[]
for _ in range(20):
    t=time.perf_counter(); timed(); samples.append((time.perf_counter()-t)*1000)
r_ms = float((out / "r_ms.txt").read_text())
py_ms = statistics.median(samples)
print(f"{name},matches={'yes' if max_diff <= 1e-8 else 'no'},max_abs_diff={max_diff:.6g},r_ms={r_ms:.6g},translated_ms={py_ms:.6g},speedup={r_ms/py_ms:.6g}")
