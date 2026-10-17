"""Proof: lscv() on R's default ev = rbox() (adaptive kd-tree, density family).

R reference: lscv-default-r.R (locfit 1.5-9.12), written to
docs/output/lscv_default_r. The d = 1 data is read from docs/output/locfit_default_r.
This script never calls R.

Case d = 1 compares R's two values (criterion, degrees of freedom) within 1e-8,
using crates/locfit lscv_tree (the default path, R's geth = 6 on the tree).

Case d = 2 is not translated: R's density path integrates over the plane
(two-dimensional density), which crates/locfit does not have. lscv raises
NotImplementedError for it; the proof records that and claims no comparison.

Timing (d = 1): one untimed call, then the median of 20 timed calls with
time.perf_counter(). speedup = R time / Python time (R: Sys.time()).

Run from the repository root:
    .venv/bin/python packages/locfit/proof/lscv-default-py.py
"""

from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _locfit10 as L  # noqa: E402

L.load_translated()
from locfit_translated.lscv import lscv  # noqa: E402

PKG = L.PKG
IN = PKG / "docs" / "output" / "locfit_default_r"
REF = PKG / "docs" / "output" / "lscv_default_r"
OUT = PKG / "docs" / "output"
PY_OUT = OUT / "lscv_default_py"
TOL = 1e-8
PROOF = "packages/locfit/proof/lscv-default-py.py"


def rd(path):
    return np.loadtxt(path, delimiter=",", ndmin=2)


def rv(path):
    return rd(path).reshape(-1)


def r_timings():
    out = {}
    for line in (REF / "timing.csv").read_text().splitlines():
        key, value = line.split(",")
        out[key] = float(value)
    return out


def time_median_ms(fn):
    """One untimed call, then the median of 20 timed calls (perf_counter), in ms."""
    fn()
    samples = []
    for _ in range(20):
        t0 = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t0) * 1000.0)
    return statistics.median(samples)


def main():
    x1 = rd(IN / "in_x1.csv").reshape(-1, 1)
    x2 = rd(IN / "in_x2.csv")
    rt = r_timings()
    PY_OUT.mkdir(parents=True, exist_ok=True)

    # d = 1: compared with R.
    got = np.asarray(lscv(x1), dtype=float)
    want = rv(REF / "lscv_d1.csv")
    worst = float(np.max(np.abs(got - want)))
    matches = worst <= TOL
    t_ms = time_median_ms(lambda: lscv(x1))
    r_ms = rt["lscv_d1"]
    line1 = (f"lscv (d = 1),matches={'yes' if matches else 'no'},max_abs_diff={worst:.3e},"
             f"r_ms={r_ms:.6g},translated_ms={t_ms:.6g},speedup={r_ms / t_ms:.4g},"
             f"proof={PROOF},python=locfit.lscv.lscv")
    detail1 = f"case=lscv_d1 criterion={abs(got[0] - want[0]):.3e} df={abs(got[1] - want[1]):.3e}"
    np.savetxt(PY_OUT / "lscv_d1.csv", got.reshape(-1, 1), delimiter=",", fmt="%.17g")

    # d = 2: not translated. Record the reason, claim no comparison.
    try:
        lscv(x2)
        line2 = "lscv (d = 2),matches=no,max_abs_diff=NA,r_ms=%.6g,translated_ms=NA,speedup=NA,blocked_by=unexpected: ran" % rt["lscv_d2"]
    except NotImplementedError as exc:
        line2 = (f"lscv (d = 2),matches=no,max_abs_diff=NA,r_ms={rt['lscv_d2']:.6g},"
                 f"translated_ms=NA,speedup=NA,blocked_by={exc}")
    detail2 = "case=lscv_d2 not translated (two-dimensional density)"

    text = "\n".join([line1, detail1, line2, detail2]) + "\n"
    (OUT / "lscv_default_compare.txt").write_text(text)
    print(text, end="")
    sys.exit(0 if matches else 1)


if __name__ == "__main__":
    main()
