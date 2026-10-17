"""qCvM from goftest 1.2-3 on the fixed inputs in qCvM-r.R.

Run from the repository root after the R script:
    Rscript packages/goftest/proof/qCvM-r.R
    .venv/bin/python packages/goftest/proof/qCvM-py.py
"""

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "packages" / "goftest"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _compare import check  # noqa: E402
from goftest.qCvM import qCvM  # noqa: E402

P = np.concatenate(([0.0, 0.001], 0.05 + 0.05 * np.arange(19, dtype=float), [0.99, 0.999, 1.0]))
TIMED_P = 0.05 + 0.05 * np.arange(19, dtype=float)


def values():
    return {
        "Inf|lower": list(qCvM(P)),
        "5|lower": list(qCvM(P, n=5)),
        "50|lower": list(qCvM(P, n=50)),
        "Inf|upper": list(qCvM(P, lower_tail=False)),
    }


def timed():
    qCvM(TIMED_P, n=50)


if __name__ == "__main__":
    sys.exit(check("qCvM", values(), timed, "qCvM (goftest 1.2-3, R) vs goftest.qCvM (Python, uniroot port)"))
