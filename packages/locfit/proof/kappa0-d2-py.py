"""Proof and timing for kappa0() at d = 2 against R (locfit 1.5-9.12).

Run from the repository root with the workspace venv (it has the locfit
crate, which supplies the geth = 2 tube constants and scritval):

    .venv/bin/python packages/locfit/proof/kappa0-d2-py.py

The R values come from kappa0-d2-r.R. The timed call is the translated
kappa0() on the same data. One untimed call, then the median of 20 timed
single calls, measured with time.perf_counter().
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parents[3]
PKG = ROOT / "packages" / "locfit" / "locfit"
OUT = ROOT / "packages" / "locfit" / "docs" / "output"
TOL = 1e-8

# Load the translated package as a namespace so its relative imports resolve.
spec = importlib.machinery.ModuleSpec("locfit_translated", loader=None,
                                      is_package=True)
spec.submodule_search_locations = [str(PKG)]
translated = importlib.util.module_from_spec(spec)
sys.modules["locfit_translated"] = translated
from locfit_translated.kappa0 import kappa0  # noqa: E402

# The same data as kappa0-d2-r.R.
i = np.arange(100)
x1 = (i + 0.5) / 100
x2 = ((37 * i) % 100 + 0.5) / 100
y = np.sin(2 * np.pi * x1) + np.cos(3 * x2) + 0.1 * x1 * x2
X = np.column_stack([x1, x2])


def read_pairs(path):
    return {k: v for k, v in
            (line.split(",", 1) for line in path.read_text().splitlines() if line)}


def median_ms(f):
    f()  # untimed call
    samples = []
    for _ in range(20):
        t0 = time.perf_counter()
        f()
        samples.append((time.perf_counter() - t0) * 1000.0)
    return statistics.median(samples)


def main():
    ref = read_pairs(OUT / "kappa0-d2-r_values.txt")
    r_ms = {k: float(v) for k, v in read_pairs(OUT / "kappa0-d2-r_timing.txt").items()}

    k95 = kappa0(X, y=y, cov=0.95)
    k90 = kappa0(X, y=y, cov=0.90)
    const = np.asarray(k95.const, dtype=float)
    r_const = np.array([float(v) for v in ref["d2_const"].split(",")])
    diffs = {
        "d2_const": float(np.max(np.abs(const - r_const))),
        "d2_d": abs(float(k95.d) - float(ref["d2_d"])),
        "d2_cov095_crit": abs(k95.crit_val - float(ref["d2_cov095_crit"])),
        "d2_cov090_crit": abs(k90.crit_val - float(ref["d2_cov090_crit"])),
    }
    values = {
        "d2_const": ",".join(repr(float(v)) for v in const),
        "d2_d": repr(int(k95.d)),
        "d2_cov095_crit": repr(k95.crit_val),
        "d2_cov090_crit": repr(k90.crit_val),
    }
    (OUT / "kappa0-d2-py_values.txt").write_text(
        "".join(f"{k},{v}\n" for k, v in values.items()))

    py_ms = median_ms(lambda: kappa0(X, y=y, cov=0.95))
    worst = max(diffs.values())
    lines = [
        f"kappa0 d=2 (n=100, cov=0.95 and 0.90),matches={'yes' if worst <= TOL else 'no'},"
        f"max_abs_diff={worst:.3e},r_ms={r_ms['d2_kappa0']:.6g},"
        f"translated_ms={py_ms:.6g},speedup={r_ms['d2_kappa0'] / py_ms:.6g},"
        f"proof=packages/locfit/proof/kappa0-d2-py.py",
    ]
    for name, diff in diffs.items():
        lines.append(f"  {name} abs_diff={diff:.3e}")
    text = "\n".join(lines) + "\n"
    (OUT / "kappa0-d2-compare.txt").write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
