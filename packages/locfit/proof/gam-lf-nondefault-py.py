"""Proof: gam.lf with non-default arguments against R locfit 1.5-9.12.

One case: gam.lf(x, y, w, alpha = 0.5, deg = 1, kern = "rect") on the g1
sample. The Python port is packages/locfit/locfit/gam_lf.py; alpha, deg and
kern go to the crate (nn, deg, kern). The R values and R timings come from
gam-lf-nondefault-r.R on the same fixed sample.

Run from the repository root with the workspace venv (it has the crate):

    .venv/bin/python packages/locfit/proof/gam-lf-nondefault-py.py

The case matches when residuals, var, and nl.df are within 1e-8 of R.

Timing: one untimed call, then the median of 20 timed calls, each timed with
time.perf_counter(). speedup = r_ms / translated_ms.
"""

from __future__ import annotations

import importlib.util
import statistics
import sys
import time
from pathlib import Path

import numpy as np

import locfit as crate  # noqa: F401  (the compiled kernel; import check)

ROOT = Path(__file__).resolve().parents[3]
PKG = ROOT / "packages" / "locfit"
OUT = PKG / "docs" / "output"
TOL = 1e-8
PROOF = "packages/locfit/proof/gam-lf-nondefault-py.py"

spec = importlib.util.spec_from_file_location("locfit_gam_lf", PKG / "locfit" / "gam_lf.py")
gam_mod = importlib.util.module_from_spec(spec)
sys.modules["locfit_gam_lf"] = gam_mod
spec.loader.exec_module(gam_mod)
gam_lf = gam_mod.gam_lf

xg1 = np.linspace(0.0, 1.0, 12)
g1 = (xg1, np.sin(2 * np.pi * xg1) + 0.1 * np.cos(7 * xg1), np.linspace(0.5, 2.0, 12))


def call():
    return gam_lf(*g1, alpha=0.5, deg=1, kern="rect")


def read_r_values():
    vals = {}
    for line in (OUT / "gam_lf_nondefault_r_values.txt").read_text().splitlines():
        case, field, text = line.split(",", 2)
        vals[field] = np.array([float(v) for v in text.split(",")])
    return vals


def read_r_timing():
    name, value = (OUT / "gam_lf_nondefault_r_timing.txt").read_text().strip().split(",")
    return float(value)


def timed_ms(fn):
    fn()  # one untimed call
    samples = []
    for _ in range(20):
        start = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - start) * 1000.0)
    return statistics.median(samples)


def main():
    ref = read_r_values()
    r_ms = read_r_timing()
    res = call()
    lines = []
    all_ok = True
    worst = 0.0
    for field in ("residuals", "var", "nl.df"):
        py = np.atleast_1d(np.asarray(res[field], dtype=float))
        rv = ref[field]
        ok = py.shape == rv.shape
        diff = float(np.max(np.abs(py - rv))) if ok else float("inf")
        ok = ok and diff <= TOL
        all_ok = all_ok and ok
        worst = max(worst, diff)
        lines.append(f"g1_nondefault {field} n={rv.size} max_abs_diff={diff:.3e} matches={ok}")

    py_ms = timed_ms(call)
    speedup = r_ms / py_ms
    OUT.mkdir(parents=True, exist_ok=True)
    summary = [
        f"proof: {PROOF}",
        f"matches: {all_ok}",
        f"max_abs_diff: {worst:.3e}",
        f"r_ms: {r_ms:.6g}",
        f"translated_ms: {py_ms:.6g}",
        f"speedup: {speedup:.4g}",
        "",
    ]
    (OUT / "gam_lf_nondefault_compare.txt").write_text("\n".join(summary + lines) + "\n")
    (OUT / "gam_lf_nondefault_python_timing.txt").write_text(f"gam.lf nondefault,{py_ms:.17g}\n")
    print("\n".join(summary + lines))


if __name__ == "__main__":
    main()
