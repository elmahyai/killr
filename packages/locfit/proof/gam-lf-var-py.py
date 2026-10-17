"""Proof: gam.lf var against R locfit 1.5-9.12.

The Python port is packages/locfit/locfit/gam_lf.py. var is the design work
array entry that R's geth = 4 path returns (see gam_lf.py). The R values and
R timings come from gam-lf-var-r.R on the same fixed samples.

Run from the repository root with the workspace venv (it has the crate):

    .venv/bin/python packages/locfit/proof/gam-lf-var-py.py

A case matches when var is within 1e-8 of R on every observation.

Timing: one untimed call, then the median of 20 timed calls, each timed with
time.perf_counter(). speedup = r_ms / translated_ms, for the first case.
"""

from __future__ import annotations

import importlib.util
import statistics
import sys
import time
from pathlib import Path
from statistics import NormalDist

import numpy as np

import locfit as crate  # noqa: F401  (the compiled kernel; import check)

ROOT = Path(__file__).resolve().parents[3]
PKG = ROOT / "packages" / "locfit"
OUT = PKG / "docs" / "output"
TOL = 1e-8
PROOF = "packages/locfit/proof/gam-lf-var-py.py"

spec = importlib.util.spec_from_file_location("locfit_gam_lf", PKG / "locfit" / "gam_lf.py")
gam_mod = importlib.util.module_from_spec(spec)
sys.modules["locfit_gam_lf"] = gam_mod
spec.loader.exec_module(gam_mod)
gam_lf = gam_mod.gam_lf

xg1 = np.linspace(0.0, 1.0, 12)
g1 = (xg1, np.sin(2 * np.pi * xg1) + 0.1 * np.cos(7 * xg1), np.linspace(0.5, 2.0, 12))
p40 = np.array([NormalDist().inv_cdf((i - 0.5) / 40) for i in range(1, 41)])
g2 = (p40, np.sin(p40) + 0.3 * np.cos(3 * p40), np.ones(40))
x1 = np.linspace(0.0, 1.0, 30)
x2 = (np.sin(np.arange(1, 31)) + 1.0) / 2.0
g3 = (np.column_stack([x1, x2]), x1 + np.sin(4 * x2), 1.0 + x1)

CALLS = {"g1_default": g1, "g2_default": g2, "g3_default": g3}


def read_r_values():
    vals = {}
    for line in (OUT / "gam_lf_var_r_values.txt").read_text().splitlines():
        case, field, text = line.split(",", 2)
        vals[case] = np.array([float(v) for v in text.split(",")])
    return vals


def read_r_timing():
    name, value = (OUT / "gam_lf_var_r_timing.txt").read_text().strip().split(",")
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
    lines = []
    all_ok = True
    worst = 0.0
    for case, (x, y, w) in CALLS.items():
        var = np.atleast_1d(np.asarray(gam_lf(x, y, w)["var"], dtype=float))
        rv = ref[case]
        ok = var.shape == rv.shape
        diff = float(np.max(np.abs(var - rv))) if ok else float("inf")
        ok = ok and diff <= TOL
        all_ok = all_ok and ok
        worst = max(worst, diff)
        lines.append(f"{case} var n={rv.size} max_abs_diff={diff:.3e} matches={ok}")

    py_ms = timed_ms(lambda: gam_lf(*g1))
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
    (OUT / "gam_lf_var_compare.txt").write_text("\n".join(summary + lines) + "\n")
    (OUT / "gam_lf_var_python_timing.txt").write_text(f"gam.lf var,{py_ms:.17g}\n")
    print("\n".join(summary + lines))


if __name__ == "__main__":
    main()
