"""ad.test from goftest 1.2-3 on the fixed inputs in ad-test-r.R.

Run from the repository root after the R script:
    Rscript packages/goftest/proof/ad-test-r.R
    .venv/bin/python packages/goftest/proof/ad-test-py.py
"""

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "packages" / "goftest"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _compare import check  # noqa: E402
from boot.rng import set_seed  # noqa: E402
from goftest.ad_test import ad_test  # noqa: E402

GOLDEN = 0.6180339887498949


def make_sample(n, family):
    i = np.arange(1, n + 1, dtype=float)
    if family == "uniform":
        u = (i * GOLDEN) % 1.0
    else:
        t = i / (n + 1)
        u = t * t
    return np.sort(u)


def values():
    res = {}
    for fam in ("uniform", "skewed"):
        for n in (5, 50, 1000):
            u = make_sample(n, fam)
            z = ad_test(u)
            res[f"stat|{fam}|{n}|punif"] = [z.statistic]
            res[f"p|{fam}|{n}|punif"] = [z.p_value]
            z = ad_test(u, "pnorm", mean=0.5, sd=0.2)
            res[f"stat|{fam}|{n}|pnorm"] = [z.statistic]
            res[f"p|{fam}|{n}|pnorm"] = [z.p_value]
            set_seed(7)
            z = ad_test(u, estimated=True)
            res[f"stat|{fam}|{n}|estimated"] = [z.statistic]
            res[f"p|{fam}|{n}|estimated"] = [z.p_value]
    return res


u_big = make_sample(10000, "uniform")


def timed():
    ad_test(u_big)


if __name__ == "__main__":
    sys.exit(check("ad-test", values(), timed, "ad.test (goftest 1.2-3, R) vs goftest.ad_test (Python)"))
