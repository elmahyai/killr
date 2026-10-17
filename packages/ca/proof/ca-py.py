import sys
import time
from pathlib import Path
import numpy as np

sys.path.insert(0, "packages/ca")
from ca import ca, cacoord, caconv, iterate_mjca, mjca

OUT = Path("packages/ca/docs/output")
tab = np.array([[12, 5, 3], [4, 11, 6], [2, 7, 13], [8, 4, 9]], float)


def rvalues(name):
    return np.loadtxt(OUT / f"{name}-r-values.csv", ndmin=1)


def align(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if a.shape != b.shape:
        return np.inf
    if a.ndim == 2:
        signs = np.where(np.sum(a * b, axis=0) < 0, -1, 1)
        a = a * signs
    return np.max(np.abs(a - b), initial=0)


def bench(fn):
    fn()
    times = []
    for _ in range(20):
        start = time.perf_counter()
        fn()
        times.append((time.perf_counter() - start) * 1000)
    return float(np.median(times))


z = ca(tab)
vals = np.r_[z["sv"], z["rowmass"], z["colmass"],
             z["rowcoord"].ravel(order="F"), z["colcoord"].ravel(order="F")]
print("ca", align(vals, rvalues("ca")), np.loadtxt(OUT/"ca-r-ms.txt"), bench(lambda: ca(tab)))
principal = cacoord(z, "principal")
vals = np.r_[principal["rows"].ravel(order="F"), principal["columns"].ravel(order="F")]
print("cacoord", np.max(np.abs(vals-rvalues("cacoord"))), "-", bench(lambda: cacoord(z, "principal")))
ind = caconv(tab, "freq", "ind")
burt = caconv(tab, "freq", "Burt")
vals = np.r_[ind.ravel(order="F"), burt.ravel(order="F")]
print("caconv", np.max(np.abs(vals-rvalues("caconv"))), "-", bench(lambda: caconv(tab, "freq", "ind")))
dat = np.array([["x", "u"], ["y", "u"], ["x", "v"], ["z", "v"], ["y", "u"]], object)
m = mjca(dat, lambda_="indicator")
vals = np.r_[m["sv"], m["rowcoord"].ravel(order="F"), m["colcoord"].ravel(order="F")]
print("mjca", align(vals, rvalues("mjca")), "-", bench(lambda: mjca(dat, lambda_="indicator")))
b = caconv(dat, "rpm", "Burt")
it = iterate_mjca(b, [3, 2], nd=2)
vals = np.r_[it["B.star"].ravel(order="F"), it["crit"]]
print("iterate_mjca", align(vals, rvalues("iterate_mjca")), "-", bench(lambda: iterate_mjca(b, [3, 2], nd=2)))
