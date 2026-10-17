"""pCvM from goftest 1.2-3 on the fixed inputs in pCvM-r.R.

Run from the repository root after the R script:
    Rscript packages/goftest/proof/pCvM-r.R
    .venv/bin/python packages/goftest/proof/pCvM-py.py
"""

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "packages" / "goftest"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _compare import check  # noqa: E402
from goftest.pCvM import pCvM  # noqa: E402

Q = np.concatenate(([0.0, 1 / 12], 0.02 + 0.02 * np.arange(30, dtype=float), [0.9, 1.5, 2.5, 5.0, 10.0, 20.0, 33.0, 34.0]))
BIG_Q = 0.001 + 0.001 * np.arange(2000, dtype=float)


def values():
    return {
        "Inf|lower": list(pCvM(Q)),
        "5|lower": list(pCvM(Q, n=5)),
        "50|lower": list(pCvM(Q, n=50)),
        "1000|lower": list(pCvM(Q, n=1000)),
        "Inf|upper": list(pCvM(Q, lower_tail=False)),
        "50|upper": list(pCvM(Q, n=50, lower_tail=False)),
    }


def timed():
    pCvM(BIG_Q, n=50)


if __name__ == "__main__":
    sys.exit(check("pCvM", values(), timed, "pCvM (goftest 1.2-3, R) vs goftest.pCvM (Python, SciPy kv)"))
