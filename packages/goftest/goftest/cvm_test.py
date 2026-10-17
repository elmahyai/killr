"""Cramer-von Mises goodness-of-fit test: goftest 1.2-3 cvm.test (R/cvmtest.R)."""

from __future__ import annotations

import math

import numpy as np

from goftest._common import HTest, braun, get_cdf, parameter_lines
from goftest.pCvM import pCvM
from goftest.recogniseCdf import recogniseCdf


def simple_cvm_test(u):
    """simpleCvMtest: the omega^2 statistic and its pCvM upper tail."""
    u = np.sort(np.asarray(u, dtype=float))
    n = u.size
    k = np.arange(1, n + 1)
    omega2 = 1.0 / (12 * n) + np.sum((u - (2 * k - 1) / (2 * n)) ** 2)
    pvalue = float(pCvM(np.array([omega2]), n=n, lower_tail=False)[0])
    return float(omega2), pvalue, "omega2"


def cvm_test(x, null="punif", *, estimated=False, nullname=None, **kwargs):
    """Cramer-von Mises test of the sample x against the null cdf.

    Arguments follow ad_test: `null` is a function or a built-in cdf name, and
    extra keyword arguments go to the cdf.
    """
    nulltext = null if isinstance(null, str) else getattr(null, "__name__", "null")
    if nullname is None:
        reco = recogniseCdf(nulltext)
        nullname = reco if reco is not None else f"distribution \u2018{nulltext}\u2019"
    x = np.asarray(x, dtype=float).ravel()
    f0 = get_cdf(null)
    u = np.asarray(f0(x, **kwargs), dtype=float)
    n = u.size
    if np.any((u < 0) | (u > 1)):
        raise ValueError("null distribution function returned values outside [0,1]")

    if not estimated or n <= 4:
        stat, pval, statname = simple_cvm_test(u)
        adjust = None
    else:
        m = round(math.sqrt(n))
        stat, pval, statname = braun(u, simple_cvm_test, m)
        adjust = f"Braun's adjustment using {m} groups"

    method = ["Cramer-von Mises test of goodness-of-fit"]
    if adjust is not None:
        method.append(adjust)
    method.append(f"Null hypothesis: {nullname}")
    method += parameter_lines(f0, kwargs)
    method.append(
        "Parameters assumed to "
        + ("have been estimated from data" if estimated else "be fixed")
    )
    return HTest(statistic=stat, p_value=pval, statistic_name=statname, method=method)
