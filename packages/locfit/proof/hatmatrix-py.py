"""Proof: the hatmatrix probe against R's data-path hat matrix. NOT the default path.

R's hatmatrix() errors on the default ev = rbox() path for every n tried
(see docs/output/hatmatrix_r/default_error.txt), so there is no default-path
reference. This script checks the Python probe (locfit/hatmatrix.py) against
R's t(locfit.raw(geth = 1, ev = dat())) on the first 40 rows of the fixed d = 1
input. The translated flag stays false until a default-path reference exists.

Timing: one untimed call, then the median of 20 timed calls with
time.perf_counter(). Python time is the probe on the same 40 rows.

Run from the repository root:
    .venv/bin/python packages/locfit/proof/hatmatrix-py.py
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

# locfit/hatmatrix.py imports the top-level locfit_raw by its bare name, as lcv does.
sys.modules.setdefault("locfit_raw", _locfit_raw_mod)
_spec = importlib.util.spec_from_file_location("locfit_hatmatrix", L.PKG / "locfit" / "hatmatrix.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
hatmatrix = _mod.hatmatrix

PKG = L.PKG
RREF = PKG / "docs" / "output" / "hatmatrix_r"
OUT = PKG / "docs" / "output"
TOL = 1e-8


def time_median_ms(fn):
    fn()
    samples = []
    for _ in range(20):
        t0 = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t0) * 1000.0)
    return statistics.median(samples)


def main():
    x1 = np.loadtxt(PKG / "docs" / "output" / "locfit_default_r" / "in_x1.csv", delimiter=",")[:40]
    y1 = np.loadtxt(PKG / "docs" / "output" / "locfit_default_r" / "in_y1.csv", delimiter=",")[:40]
    want = np.loadtxt(RREF / "dat_hat.csv", delimiter=",", ndmin=2)
    got = hatmatrix(x1.reshape(-1, 1), y=y1)
    worst = float(np.max(np.abs(got - want)))
    matches = worst <= TOL
    r_ms = float(open(RREF / "timing.csv").read().split(",")[1])
    t_ms = time_median_ms(lambda: hatmatrix(x1.reshape(-1, 1), y=y1))
    line = (f"hatmatrix (data path, not default),matches={'yes' if matches else 'no'},"
            f"max_abs_diff={worst:.3e},r_ms={r_ms:.6g},translated_ms={t_ms:.6g},"
            f"speedup={r_ms / t_ms:.4g},proof=packages/locfit/proof/hatmatrix-py.py,"
            f"python=locfit.hatmatrix.hatmatrix")
    print(line)
    (OUT / "hatmatrix_compare.txt").write_text(
        line + "\n" + (RREF / "default_error.txt").read_text())
    sys.exit(0 if matches else 1)


if __name__ == "__main__":
    main()
