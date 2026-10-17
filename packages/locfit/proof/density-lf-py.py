"""Proof: density.lf against R locfit 1.5-9.12.

The Python port is packages/locfit/locfit/density_lf.py, which calls the
density-family kernel in crates/locfit (density_lf.rs). The R values and
R timings come from density-lf-r.R on the same fixed samples.

Run from the repository root with the workspace venv (it has the crate):

    .venv/bin/python packages/locfit/proof/density-lf-py.py

A case matches when the grid and the density values are within 1e-8 of R.

Timing: one untimed call, then the median of 20 timed calls, each timed with
time.perf_counter(). speedup = r_ms / translated_ms, for the default case.
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
PROOF = "packages/locfit/proof/density-lf-py.py"

spec = importlib.util.spec_from_file_location("locfit_density_lf", PKG / "locfit" / "density_lf.py")
dl_mod = importlib.util.module_from_spec(spec)
sys.modules["locfit_density_lf"] = dl_mod
spec.loader.exec_module(dl_mod)
density_lf = dl_mod.density_lf

from statistics import NormalDist  # noqa: E402

xd = np.array([NormalDist().inv_cdf(p) for p in np.linspace(0.05, 0.95, 20)])
# ppoints(60) = (i - 0.5) / 60 for i = 1..60 (R's a = 0.5 for n > 10).
x2 = np.array([NormalDist().inv_cdf((i - 0.5) / 60) for i in range(1, 61)]) * 1.3 + 0.2

CALLS = {
    "xd_default": (xd, {}),
    "xd_rect": (xd, {"window": "rectangular"}),
    "xd_tria": (xd, {"window": "triangular"}),
    "xd_tcub": (xd, {"window": "tcub"}),
    "x2_default": (x2, {}),
    "x2_width": (x2, {"n": 80, "width": 0.8}),
}


def read_r_values():
    vals = {}
    for line in (OUT / "density_lf_r_values.txt").read_text().splitlines():
        case, field, text = line.split(",", 2)
        vals[(case, field)] = np.array([float(v) for v in text.split(",")])
    return vals


def read_r_timing():
    name, value = (OUT / "density_lf_r_timing.txt").read_text().strip().split(",")
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
    py_lines = []
    all_ok = True
    for case, (x, kw) in CALLS.items():
        res = density_lf(x, **kw)
        for field in ("x", "y"):
            py = np.asarray(res[field], dtype=float)
            rv = ref[(case, field)]
            ok = py.shape == rv.shape
            diff = float(np.max(np.abs(py - rv))) if ok else float("inf")
            ok = ok and diff <= TOL
            all_ok = all_ok and ok
            lines.append(f"{case} {field} n={rv.size} max_abs_diff={diff:.3e} matches={ok}")
            py_lines.append(f"{case},{field}," + ",".join(f"{v:.17g}" for v in py))

    py_ms = timed_ms(lambda: density_lf(xd))
    speedup = r_ms / py_ms
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "density_lf_python_values.txt").write_text("\n".join(py_lines) + "\n")
    (OUT / "density_lf_python_timing.txt").write_text(f"density.lf,{py_ms:.17g}\n")
    summary = [
        f"proof: {PROOF}",
        f"matches: {all_ok}",
        f"max_abs_diff: {max(float(l.split('max_abs_diff=')[1].split()[0]) for l in lines):.3e}",
        f"r_ms: {r_ms:.6g}",
        f"translated_ms: {py_ms:.6g}",
        f"speedup: {speedup:.4g}",
        "",
    ]
    (OUT / "density_lf_compare.txt").write_text("\n".join(summary + lines) + "\n")
    print("\n".join(summary + lines))


if __name__ == "__main__":
    main()
