"""Proof, Python side for mgibbsbd (the Fortran routine behind pan.bd()). Calls
packages/pan/pan/mgibbsbd.py on the fixed fixture, times it, and compares every output
and the final state with the R output that mgibbsbd_r.R wrote.

Usage (run mgibbsbd_r.R first):
    .venv/bin/python packages/pan/proof/mgibbsbd_py.py

Each call: one untimed call, then the median of 20 timed calls (time.perf_counter()).
The timed call is the whole wrapper: the checks, the index work, rngs, and the kernel.
"""

import statistics
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PKG = HERE.parent  # packages/pan, which holds the pan/ package
FIX = HERE / "fixture"
OUT = HERE.parent / "docs" / "output"
sys.path.insert(0, str(PKG))

from pan.mgibbsbd import mgibbsbd  # noqa: E402

SEED = 20261017
ITER = 200
TOL = 1e-8
XCOL = [1, 2, 3]
ZCOL = [1, 2]
BLOCKS = ["betas", "sigmas", "psis", "y", "last_beta", "last_sigma", "last_psi", "last_y"]


def load_fixture():
    subj = np.loadtxt(FIX / "subj.csv", dtype=np.int64, ndmin=1)
    pred = np.loadtxt(FIX / "pred.csv", delimiter=",", ndmin=2)
    rows = [line.strip().split(",") for line in open(FIX / "y.csv")]
    y = np.array([[np.nan if v == "NA" else float(v) for v in row] for row in rows])
    return subj, pred, y


def read_r_blocks(path):
    blocks, times, median = {}, None, None
    lines = path.read_text().splitlines()
    i = 0
    while i < len(lines):
        parts = lines[i].split()
        if parts[0] == "BLOCK":
            name, dims = parts[1], tuple(int(d) for d in parts[2].split(","))
            n = int(np.prod(dims))
            vals = np.array([float(v) for v in lines[i + 1 : i + 1 + n]])
            blocks[name] = vals.reshape(dims, order="F")
            i += 1 + n
        elif parts[0] == "TIMES":
            times = [float(v) for v in parts[1:]]
            i += 1
        elif parts[0] == "MEDIAN":
            median = float(parts[1])
            i += 1
        else:
            i += 1
    return blocks, times, median


def main():
    subj, pred, y = load_fixture()
    ntot, r = y.shape
    q = len(ZCOL)

    # Same values as mgibbsbd_r.R: identity Binv, c = 3 for each response, identity Dinv blocks.
    prior = dict(
        a=3.0,
        Binv=np.eye(r),
        c=np.full(r, 3.0),
        Dinv=np.stack([np.eye(q)] * r, axis=2),  # q x q x r, one block per response
    )

    def one_call():
        return mgibbsbd(y, subj, pred, XCOL, ZCOL, prior, SEED, iter=ITER)

    out = one_call()  # untimed
    times = []
    for _ in range(20):
        t0 = time.perf_counter()
        one_call()
        times.append(time.perf_counter() - t0)
    median_py = float(statistics.median(times))

    r_blocks, _, r_median = read_r_blocks(OUT / "r_mgibbsbd.txt")
    py = {
        "betas": out["beta"], "sigmas": out["sigma"], "psis": out["psi"], "y": out["y"],
        "last_beta": out["last"]["beta"], "last_sigma": out["last"]["sigma"],
        "last_psi": out["last"]["psi"], "last_y": out["last"]["y"],
    }

    lines = [f"Proof: mgibbsbd wrapper (pan.mgibbsbd.mgibbsbd) vs R pan 2.0 pan.bd() on the fixed "
             f"fixture (seed {SEED}, iter {ITER}, ntot {ntot}, tol {TOL:g})"]
    max_all = 0.0
    all_ok = True
    for name in BLOCKS:
        rv = r_blocks[name]
        pv = np.asarray(py[name], dtype=float)
        if rv.shape != pv.shape:
            lines.append(f"{name}: shape mismatch R {rv.shape} vs Python {pv.shape}")
            all_ok = False
            continue
        diff = float(np.max(np.abs(rv - pv)))
        max_all = max(max_all, diff)
        ok = diff <= TOL
        all_ok = all_ok and ok
        lines.append(f"{name:10s} shape={pv.shape} max_abs_diff={diff:.3e} {'PASS' if ok else 'FAIL'}")
    lines.append(f"max_abs_diff over all outputs = {max_all:.3e}")
    lines.append(f"Result: {'PASS' if all_ok else 'FAIL'} (tolerance {TOL:g})")
    lines.append(f"R median of 20 timed calls (Sys.time): {r_median:.6f} s")
    lines.append(f"Python median of 20 timed calls (perf_counter), wrapper + rngs + kernel: {median_py:.6f} s")
    lines.append(f"speedup (R / Python) = {r_median / median_py:.2f}")
    text = "\n".join(lines) + "\n"
    print(text, end="")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "mgibbsbd_compare.txt").write_text(text)

    with open(OUT / "py_mgibbsbd.txt", "w") as fh:
        for name in BLOCKS:
            pv = np.asarray(py[name], dtype=float)
            fh.write(f"BLOCK {name} {','.join(str(d) for d in pv.shape)}\n")
            fh.write("".join(f"{v:.17g}\n" for v in pv.reshape(-1, order="F")))
        fh.write("TIMES " + " ".join(f"{t:.9g}" for t in times) + "\n")
        fh.write(f"MEDIAN {median_py:.9g}\n")

    if not all_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
