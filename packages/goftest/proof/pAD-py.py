"""pAD from goftest 1.2-3 on the fixed inputs in pAD-r.R.

Run from the repository root after the R script:
    Rscript packages/goftest/proof/pAD-r.R
    .venv/bin/python packages/goftest/proof/pAD-py.py
"""

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "packages" / "goftest"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _compare import check  # noqa: E402
from goftest.pAD import pAD  # noqa: E402

GRID = 0.05 + 0.1 * np.arange(60, dtype=float)
BIG_GRID = 0.05 + 0.0005 * np.arange(10000, dtype=float)
SPECIAL = np.array([-np.inf, -1.0, 0.0, 1e-3, 0.5, 2.0, 10.0, 50.0, np.inf, np.nan])


def values():
    return {
        "grid|Inf|fast": list(pAD(GRID)),
        "grid|Inf|exact": list(pAD(GRID, fast=False)),
        "grid|Inf|upper": list(pAD(GRID, lower_tail=False)),
        "grid|5": list(pAD(GRID, n=5)),
        "grid|50": list(pAD(GRID, n=50)),
        "grid|1000": list(pAD(GRID, n=1000)),
        "grid|50|upper": list(pAD(GRID, n=50, lower_tail=False)),
        "special|Inf|fast": list(pAD(SPECIAL)),
        "special|50": list(pAD(SPECIAL, n=50)),
    }


def timed():
    pAD(BIG_GRID)


if __name__ == "__main__":
    sys.exit(check("pAD", values(), timed, "pAD (goftest 1.2-3, R) vs goftest.pAD (Python, goftest_kernels)"))
