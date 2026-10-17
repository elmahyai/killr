"""Proof: smooth.lf() on R's default path (direct = FALSE, ev = rbox()).

R reference: smooth-lf-r.R (locfit 1.5-9.12), written to docs/output/smooth_lf_r.
The inputs are the fixed files written by locfit-default-r.R, read here. This
script never calls R.

Each case compares the smoothed y with R within 1e-8. xev defaults to x, so the
values are the tree fit's fitted values from crates/locfit.

Timing: one untimed call, then the median of 20 timed calls with
time.perf_counter(). speedup = R time / Python time (R: Sys.time()).

Run from the repository root:
    .venv/bin/python packages/locfit/proof/smooth-lf-py.py
"""

from __future__ import annotations

import importlib
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _locfit10 as L  # noqa: E402

import importlib.util  # noqa: E402

L.load_translated()
import locfit_translated.locfit_raw as _locfit_raw_mod  # noqa: E402

# locfit/smooth_lf.py imports the top-level locfit_raw by its bare name when it is
# loaded by file path, as lcv-default-py.py does. Alias it instead of putting
# packages/locfit on sys.path, where the top-level locfit.py would shadow the crate.
sys.modules.setdefault("locfit_raw", _locfit_raw_mod)
_spec = importlib.util.spec_from_file_location("locfit_smooth_lf", L.PKG / "locfit" / "smooth_lf.py")
_smooth_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_smooth_mod)
smooth_lf = _smooth_mod.smooth_lf

PKG = L.PKG
REF = PKG / "docs" / "output" / "locfit_default_r"
RREF = PKG / "docs" / "output" / "smooth_lf_r"
OUT = PKG / "docs" / "output"
PY_OUT = OUT / "smooth_lf_py"
TOL = 1e-8
PROOF = "packages/locfit/proof/smooth-lf-py.py"


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
    x1 = rd(REF / "in_x1.csv")
    y1 = rd(REF / "in_y1.csv").reshape(-1)
    x2 = rd(REF / "in_x2.csv")
    y2 = rd(REF / "in_y2.csv").reshape(-1)
    cases = {
        "smooth_lf_d1": (lambda: smooth_lf(x1, y1), {}),
        "smooth_lf_d2": (lambda: smooth_lf(x2, y2), {}),
        "smooth_lf_d1_alpha": (lambda: smooth_lf(x1, y1, alpha=0.5, deg=1), {}),
    }
    timing = {}
    for line in (RREF / "timing.csv").read_text().splitlines():
        key, value = line.split(",")
        timing[key] = float(value)

    PY_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    ok = True
    for name, (call, _) in cases.items():
        got = np.asarray(call()["y"], dtype=float).reshape(-1)
        want = rd(RREF / f"{name}.csv").reshape(-1)
        worst = float(np.max(np.abs(got - want)))
        matches = worst <= TOL and got.shape == want.shape
        ok = ok and matches
        t_ms = time_median_ms(call)
        r_ms = timing[name]
        rows.append(
            f"smooth.lf ({name.removeprefix('smooth_lf_')}),matches={'yes' if matches else 'no'},"
            f"max_abs_diff={worst:.3e},r_ms={r_ms:.6g},translated_ms={t_ms:.6g},"
            f"speedup={r_ms / t_ms:.4g},proof={PROOF},python=locfit.smooth_lf.smooth_lf"
        )
        np.savetxt(PY_OUT / f"{name}.csv", got.reshape(-1, 1), delimiter=",", fmt="%.17g")
        print(rows[-1])

    # Not in the matching set: the calls outside the default path must raise.
    for label, call in {
        "direct=TRUE": lambda: smooth_lf(x1, y1, direct=True),
        "new xev": lambda: smooth_lf(x1, y1, xev=np.linspace(0, 1, 7)),
    }.items():
        try:
            call()
            rows.append(f"smooth.lf ({label}),matches=not-implemented-raised-no")
        except NotImplementedError as exc:
            rows.append(f"smooth.lf ({label}),NotImplementedError: {exc}")
    text = "\n".join(rows) + "\n"
    (OUT / "smooth_lf_compare.txt").write_text(text)
    print(text)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
