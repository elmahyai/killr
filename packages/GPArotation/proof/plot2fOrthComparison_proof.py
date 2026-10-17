import csv
import sys
import time

import matplotlib
matplotlib.use("Agg")
import numpy as np

sys.path.insert(0, "packages/GPArotation")
from GPArotation.plot2fOrthComparison import _trace, plot2fOrthComparison

A = np.array([[.8, .1], [.1, .7], [.2, .2], [.6, .2], [.2, .8], [.3, .2]])
kwargs = {}

with open("packages/GPArotation/docs/output/plot2fOrthComparison_r.csv") as fh:
    refs = {row[0]: np.array([float(x) for x in row[1:]]) for row in csv.reader(fh)}

def data_call():
    out = {name: _trace(A, "quartimax", name, 30, kwargs)
           for name in ("legacy", "bb", "cayley")}
    theta = np.linspace(0, 2 * np.pi, 101)
    from GPArotation.core import criterion
    landscape = np.array([
        criterion(A @ np.array([[np.cos(t), -np.sin(t)],
                                [np.sin(t), np.cos(t)]]),
                  "quartimax", kwargs)["f"] for t in theta])
    return out, theta, landscape

untimed = data_call()
times = []
for _ in range(20):
    start = time.perf_counter()
    data_call()
    times.append((time.perf_counter() - start) * 1000)
translated_ms = float(np.median(times))
r_ms = float(open(
    "packages/GPArotation/docs/output/plot2fOrthComparison_r_ms.txt").read())
values = []
for name in ("legacy", "bb", "cayley"):
    values.append(np.ravel(A @ untimed[0][name]["T"][-1], order="F"))
values.extend((untimed[2], untimed[1]))
diffs = [np.max(np.abs(values[i] - refs[name]))
         for i, name in enumerate(("legacy_loadings", "bb_loadings",
                                   "cayley_loadings", "landscape", "theta"))]
max_abs_diff = float(max(diffs))
result = plot2fOrthComparison(A, nang=101, maxit=30)
result["figure"].savefig(
    "packages/GPArotation/docs/output/plot2fOrthComparison.svg", format="svg")
with open("packages/GPArotation/docs/output/plot2fOrthComparison_python.txt", "w") as fh:
    fh.write("matches=%s max_abs_diff=%.17g r_ms=%.6f translated_ms=%.6f "
             "speedup=%.6f\n" % (
                 max_abs_diff <= 1e-8, max_abs_diff, r_ms, translated_ms,
                 r_ms / translated_ms))
print(open("packages/GPArotation/docs/output/plot2fOrthComparison_python.txt").read(),
      end="")
