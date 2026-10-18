"""Proof for crates/deldir, Python side.

Runs the Rust kernels (deldir_engine: binsrt, master, intri) on the point sets
written by kernel-r.R, and compares them with the reference outputs of the
installed deldir 2.0-4 .Fortran entry points.

Run kernel-r.R first, from the repository root:
    .venv/bin/python packages/deldir/proof/kernel-py.py
"""

import json
import statistics
import time
from pathlib import Path

import numpy as np

from deldir_engine import binsrt, intri, master

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "packages" / "deldir" / "docs" / "output"
TOL = 1e-8
REPS = 20

ref = json.loads((OUT / "kernel-r-reference.json").read_text())
EPS = ref["eps"]


def window(x, y):
    """Window as deldir() builds it: data range plus 10 percent on each side."""
    xdff = float(x.max() - x.min())
    ydff = float(y.max() - y.min())
    return np.array(
        [
            float(x.min()) - 0.1 * xdff,
            float(x.max()) + 0.1 * xdff,
            float(y.min()) - 0.1 * ydff,
            float(y.max()) + 0.1 * ydff,
        ]
    )


def chain(x, y, rw, tri, ux, uy):
    """One pass of the kernel work: binsrt, master, and intri per candidate."""
    tx, ty, ind, rind = binsrt(x, y, rw)
    delsgs, delsum, dirsgs, dirsum = master(tx, ty, rw, EPS)
    okay = np.empty(len(tri), dtype=np.int64)
    for i in range(len(tri)):
        okay[i] = intri(tri[i, 0:3], tri[i, 3:6], ux, uy)
    return tx, ty, ind, rind, delsgs, delsum, dirsgs, dirsum, okay


def maxdiff(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.shape != b.shape:
        return float("inf")
    if a.size == 0:
        return 0.0
    return float(np.max(np.abs(a - b)))


def exact(a, b):
    a = np.asarray(a)
    b = np.asarray(b)
    return a.shape == b.shape and bool(np.array_equal(a, b))


lines = []
all_ok = True
worst = 0.0
for case in ref["cases"]:
    n = case["n"]
    pts = np.loadtxt(OUT / f"points-{n}.csv", delimiter=",", skiprows=1, ndmin=2)
    x = np.ascontiguousarray(pts[:, 0])
    y = np.ascontiguousarray(pts[:, 1])
    tri_raw = np.loadtxt(OUT / f"triangles-{n}.csv", delimiter=",", skiprows=1, ndmin=2)
    tri = np.ascontiguousarray(tri_raw)  # columns x1,x2,x3,y1,y2,y3
    rw = window(x, y)

    # One untimed run, then the median of REPS timed runs (perf_counter).
    out = chain(x, y, rw, tri, x, y)
    times = []
    for _ in range(REPS):
        started = time.perf_counter()
        out = chain(x, y, rw, tri, x, y)
        times.append((time.perf_counter() - started) * 1000.0)
    translated_ms = statistics.median(times)
    r_ms = float(case["r_ms"])

    tx, ty, ind, rind, delsgs, delsum, dirsgs, dirsum, okay = out

    ok_rw = maxdiff(rw, case["rw"])
    ok_bin_f = max(maxdiff(tx, case["binsrt"]["tx"]), maxdiff(ty, case["binsrt"]["ty"]))
    ok_bin_i = exact(ind, case["binsrt"]["ind"]) and exact(rind, case["binsrt"]["rind"])

    ndel = len(delsgs)
    ndir = len(dirsgs)
    m = case["master"]
    counts_ok = ndel == m["ndel"] and ndir == m["ndir"]

    ref_delsgs = np.array(m["delsgs"], dtype=float)
    ref_dirsgs = np.array(m["dirsgs"], dtype=float)
    ref_delsum = np.array(m["delsum"], dtype=float)
    ref_dirsum = np.array(m["dirsum"], dtype=float)

    # Index columns must match exactly: delsgs ind1, ind2; dirsgs ind1, ind2,
    # bp1, bp2, thirdv1, thirdv2.
    idx_ok = (
        exact(delsgs[:, 4:6], ref_delsgs[:, 4:6])
        and exact(dirsgs[:, 4:10], ref_dirsgs[:, 4:10])
    )
    f_master = max(
        maxdiff(delsgs[:, 0:4], ref_delsgs[:, 0:4]),
        maxdiff(dirsgs[:, 0:4], ref_dirsgs[:, 0:4]),
        maxdiff(delsum, ref_delsum),
        maxdiff(dirsum, ref_dirsum),
    )
    okay_ok = exact(okay, case["okay"])

    case_ok = (
        ok_rw <= TOL
        and ok_bin_f <= TOL
        and ok_bin_i
        and counts_ok
        and idx_ok
        and f_master <= TOL
        and okay_ok
    )
    case_diff = max(ok_rw, ok_bin_f, f_master)
    all_ok = all_ok and case_ok
    worst = max(worst, case_diff)

    speedup = r_ms / translated_ms
    lines.append(
        f"n={n} matches={case_ok} max_abs_diff={case_diff:.3e} "
        f"ndel={ndel} ndir={ndir} delaunay_triangles(intri ok)={int(okay.sum())} "
        f"r_ms={r_ms:.4f} translated_ms={translated_ms:.4f} speedup={speedup:.2f}"
    )

summary = [
    "deldir_engine (Rust) vs deldir 2.0-4 .Fortran: binsrt, master, intri",
    f"tolerance={TOL:g} on reals; index columns and intri okay must match exactly",
    f"timed runs per size={REPS}; timer=time.perf_counter(); R timer=Sys.time()",
    f"overall matches={all_ok} max_abs_diff={worst:.3e}",
] + lines
(OUT / "kernel-py.txt").write_text("\n".join(summary) + "\n")
print("\n".join(summary))
