"""Proof: lcv() on R's default ev = rbox() (adaptive kd-tree).

R reference: lcv-default-r.R (locfit 1.5-9.12), written to
docs/output/lcv_default_r. The inputs are the fixed files written by
locfit-default-r.R, read here. This script never calls R.

Each case compares lik, infl, vari and cv with R within 1e-8. lik, infl and vari
are the lk, df1 and df2 of the fit's dp; cv is the leave-one-out sum on the tree
(locfit fitted.c, cv branch), computed in crates/locfit.

Timing: one untimed call, then the median of 20 timed calls with
time.perf_counter(). speedup = R time / Python time (R: Sys.time()).

Run from the repository root:
    .venv/bin/python packages/locfit/proof/lcv-default-py.py
"""

from __future__ import annotations

import importlib.util
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _locfit10 as L  # noqa: E402

L.load_translated()
import locfit_translated.locfit_raw as _locfit_raw_mod  # noqa: E402

# locfit/lcv.py imports the top-level locfit_raw by its bare name, as the other
# proofs of this package expect. Alias it here instead of putting packages/locfit
# on sys.path, where the top-level locfit.py would shadow the compiled crate.
sys.modules.setdefault("locfit_raw", _locfit_raw_mod)
_spec = importlib.util.spec_from_file_location("locfit_lcv_default", L.PKG / "locfit" / "lcv.py")
_lcv_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_lcv_mod)
lcv = _lcv_mod.lcv

PKG = L.PKG
REF = PKG / "docs" / "output" / "locfit_default_r"
RREF = PKG / "docs" / "output" / "lcv_default_r"
OUT = PKG / "docs" / "output"
PY_OUT = OUT / "lcv_default_py"
TOL = 1e-8
PROOF = "packages/locfit/proof/lcv-default-py.py"
NAMES = ("lik", "infl", "vari", "cv")


def rd(path):
    return np.loadtxt(path, delimiter=",", ndmin=2)


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
    x1 = rd(REF / "in_x1.csv").reshape(-1, 1)
    y1 = rd(REF / "in_y1.csv").reshape(-1)
    x2 = rd(REF / "in_x2.csv")
    y2 = rd(REF / "in_y2.csv").reshape(-1)
    cases = {
        "lcv_d1": (x1, y1),
        "lcv_d2": (x2, y2),
    }
    timing = {}
    for line in (RREF / "timing.csv").read_text().splitlines():
        key, value = line.split(",")
        timing[key] = float(value)

    PY_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    detail = []
    ok = True
    for name, (x, y) in cases.items():
        got = lcv(x, y)
        g = np.array([got[k] for k in NAMES], dtype=float)
        want = rd(RREF / f"{name}.csv").reshape(-1)
        worst = float(np.max(np.abs(g - want)))
        matches = worst <= TOL
        ok = ok and matches
        t_ms = time_median_ms(lambda: lcv(x, y))
        r_ms = timing[name]
        rows.append(
            f"lcv ({name.split('_')[1]}),matches={'yes' if matches else 'no'},"
            f"max_abs_diff={worst:.3e},r_ms={r_ms:.6g},translated_ms={t_ms:.6g},"
            f"speedup={r_ms / t_ms:.4g},proof={PROOF},python=locfit.lcv.lcv"
        )
        detail.append(f"case={name} " + " ".join(
            f"{k}={abs(a - b):.3e}" for k, a, b in zip(NAMES, g, want)))
        np.savetxt(PY_OUT / f"{name}.csv", g.reshape(-1, 1), delimiter=",", fmt="%.17g")
        print(rows[-1])
        print(detail[-1])

    text = "\n".join(rows) + "\n" + "\n".join(detail) + "\n"
    (OUT / "lcv_default_compare.txt").write_text(text)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
