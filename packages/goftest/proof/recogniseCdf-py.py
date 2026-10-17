"""recogniseCdf from goftest 1.2-3 on the fixed inputs in recogniseCdf-r.R.

Run from the repository root after the R script:
    Rscript packages/goftest/proof/recogniseCdf-r.R
    .venv/bin/python packages/goftest/proof/recogniseCdf-py.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "packages" / "goftest"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _compare import check  # noqa: E402
from goftest.recogniseCdf import recogniseCdf  # noqa: E402

CASES = ["punif", "pnorm", "norm", "t", "pt", "chisq", "unif", "AD", "pAD", "CvM",
         "pCvM", "wilcox", "pwilcox", "p", "", "foo", "pfoo", "beta", "binom",
         "birthday", "tukey", "weibull", "nbinom", "logis", "lnorm", "gamma", "f",
         "geom", "hyper", "exp", "pois", "cauchy", "pexp", "pAD ", 1]


def _name(s):
    r = recogniseCdf(s)
    return "NULL" if r is None else r


def values():
    return {f"s|{i}": [_name(s)] for i, s in enumerate(CASES, start=1)}


def timed():
    for s in CASES:
        recogniseCdf(s)


if __name__ == "__main__":
    sys.exit(check("recogniseCdf", values(), timed, "recogniseCdf (goftest 1.2-3, R) vs goftest.recogniseCdf (Python)"))
