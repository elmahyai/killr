"""Proof: GPArotation.oblimax (Python) against R GPArotation 2026.8-2 oblimax.

Run R first (oblimax_r.R), which writes docs/output/oblimax_r.csv. Then run from the repository root:
    python3 packages/GPArotation/proof/oblimax_proof.py
Writes docs/output/oblimax_python.txt. Tolerance is 1e-8 on loadings, Phi and criterion, and equal iteration count.
"""
import csv
import sys
import time

import numpy as np

sys.path.insert(0, "packages/GPArotation")
import GPArotation as g  # noqa: E402

TOL = 1e-8
A = np.array(
    [[.8, .1, .2], [.2, .7, .1], [.1, .2, .9], [.6, .2, .3], [.2, .8, .4]], float
)
Tm = np.array([[1.0, .1, 0.], [0., 1., .2], [.1, 0., 1.]])
cases = {
    "default": lambda: g.oblimax(A),
    "normalize": lambda: g.oblimax(A, normalize=True),
    "tmat": lambda: g.oblimax(A, Tmat=Tm),
}


def _iterations(result):
    return int(result["Table"][-1, 0])


with open("packages/GPArotation/docs/output/oblimax_r.csv") as fh:
    refs = {}
    for row in csv.reader(fh):
        name, r_ms, iters, f = row[0], float(row[1]), int(row[2]), float(row[3])
        vals = np.array([float(x) for x in row[4:]])
        refs[name] = (r_ms, iters, f, vals[:15].reshape(5, 3, order="F"), vals[15:].reshape(3, 3, order="F"))

lines = []
for name, fn in cases.items():
    result = fn()  # untimed call
    r_ms, r_iters, r_f, r_load, r_phi = refs[name]
    py_iters = _iterations(result)
    py_f = float(result["Table"][-1, 1])
    d_load = float(np.max(np.abs(result["loadings"] - r_load)))
    d_phi = float(np.max(np.abs(result["Phi"] - r_phi)))
    d_f = abs(py_f - r_f)
    max_diff = max(d_load, d_phi, d_f)
    matches = max_diff <= TOL and py_iters == r_iters
    times = []
    for _ in range(20):
        start = time.perf_counter()
        fn()
        times.append((time.perf_counter() - start) * 1000)
    py_ms = float(np.median(times))
    lines.append(
        f"{name} matches={'yes' if matches else 'no'} max_abs_diff={max_diff:.3e} "
        f"loadings_diff={d_load:.3e} phi_diff={d_phi:.3e} criterion_diff={d_f:.3e} "
        f"iter_r={r_iters} iter_python={py_iters} "
        f"r_ms={r_ms:.6f} translated_ms={py_ms:.6f} speedup={r_ms / py_ms:.6f}"
    )
print("\n".join(lines))
with open("packages/GPArotation/docs/output/oblimax_python.txt", "w") as fh:
    fh.write("\n".join(lines) + "\n")
