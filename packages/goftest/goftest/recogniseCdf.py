"""recogniseCdf: the name R gives a null distribution, from goftest 1.2-3 (R/recog.R)."""

from __future__ import annotations

_DISTRIBUTIONS = {
    "beta": "beta",
    "binom": "binomial",
    "birthday": "birthday coincidence",
    "cauchy": "Cauchy",
    "chisq": "chi-squared",
    "exp": "exponential",
    "f": "F",
    "gamma": "Gamma",
    "geom": "geometric",
    "hyper": "hypergeometric",
    "lnorm": "log-normal",
    "logis": "logistic",
    "nbinom": "negative binomial",
    "norm": "Normal",
    "pois": "Poisson",
    "t": "Student's t",
    "tukey": "Tukey (Studentized range)",
    "unif": "uniform",
    "weibull": "Weibull",
}

_TESTS = {
    "AD": "Anderson-Darling",
    "CvM": "Cramer-von Mises",
    "wilcox": "Wilcoxon Rank Sum",
}


def recogniseCdf(s="punif"):
    """Return the null's name, or None when R returns NULL."""
    if not isinstance(s, str) or len(s) == 0:
        return None
    root = s[1:] if s[0] == "p" else s
    if root in _DISTRIBUTIONS:
        return f"{_DISTRIBUTIONS[root]} distribution"
    if root in _TESTS:
        return f"null distribution of {_TESTS[root]} Test Statistic"
    return None
