"""Anderson-Darling goodness-of-fit test: goftest 1.2-3 ad.test (R/andarl.R)."""

from __future__ import annotations

import math

import numpy as np

import goftest_kernels as gk

from goftest._common import HTest, braun, get_cdf, parameter_lines
from goftest.recogniseCdf import recogniseCdf


def simple_ad_test(u):
    """simpleADtest: the Marsaglia kernel on the sorted sample."""
    stat, pval = gk.ad_test(np.sort(np.asarray(u, dtype=float)))
    return float(stat), float(pval), "An"


def ad_test(x, null="punif", *, estimated=False, nullname=None, **kwargs):
    """Anderson-Darling test of the sample x against the null cdf.

    `null` is a function or the name of a built-in cdf ("punif", "pnorm").
    Extra keyword arguments go to the cdf, as `...` does in R.
    """
    nulltext = null if isinstance(null, str) else getattr(null, "__name__", "null")
    if nullname is None:
        reco = recogniseCdf(nulltext)
        nullname = reco if reco is not None else f"distribution \u2018{nulltext}\u2019"
    x = np.asarray(x, dtype=float).ravel()
    n = x.size
    f0 = get_cdf(null)
    u = np.asarray(f0(x, **kwargs), dtype=float)
    if np.any((u < 0) | (u > 1)):
        raise ValueError("null distribution function returned values outside [0,1]")

    if not estimated or n <= 4:
        stat, pval, statname = simple_ad_test(u)
        adjust = None
    else:
        m = round(math.sqrt(n))
        stat, pval, statname = braun(u, simple_ad_test, m)
        adjust = f"Braun's adjustment using {m} groups"

    method = ["Anderson-Darling test of goodness-of-fit"]
    if adjust is not None:
        method.append(adjust)
    method.append(f"Null hypothesis: {nullname}")
    method += parameter_lines(f0, kwargs)
    method.append(
        "Parameters assumed to "
        + ("have been estimated from data" if estimated else "be fixed")
    )
    return HTest(statistic=stat, p_value=pval, statistic_name=statname, method=method)
