"""qAD from goftest 1.2-3 on the fixed inputs in qAD-r.R.

Run from the repository root after the R script:
    Rscript packages/goftest/proof/qAD-r.R
    .venv/bin/python packages/goftest/proof/qAD-py.py
"""

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "packages" / "goftest"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _compare import check  # noqa: E402
from goftest.qAD import qAD  # noqa: E402

P = np.concatenate(([0.0, 0.001], 0.05 + 0.05 * np.arange(19, dtype=float), [0.99, 0.999, 1.0]))
TIMED_P = 0.05 + 0.05 * np.arange(19, dtype=float)


def values():
    return {
        "Inf|fast|lower": list(qAD(P)),
        "Inf|exact|lower": list(qAD(P, fast=False)),
        "Inf|fast|upper": list(qAD(P, lower_tail=False)),
        "5|fast|lower": list(qAD(P, n=5)),
        "50|fast|lower": list(qAD(P, n=50)),
        "1000|fast|lower": list(qAD(P, n=1000)),
    }


def timed():
    qAD(TIMED_P, n=50)


if __name__ == "__main__":
    sys.exit(check("qAD", values(), timed, "qAD (goftest 1.2-3, R) vs goftest.qAD (Python, uniroot port)"))
