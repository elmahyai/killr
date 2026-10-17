"""Hall-Sheather and Bofinger bandwidths for the sparsity estimate."""

from __future__ import annotations

from scipy.stats import norm


def bandwidth_rq(p, n, hs=True, alpha=0.05):
    """Bandwidth for the sparsity estimate used by summary.rq.

    hs=True is Hall and Sheather, rate n^(-1/3). hs=False is Bofinger,
    rate n^(-1/5). qnorm and dnorm are SciPy, which match R inside 1e-15.
    """
    x0 = float(norm.ppf(p))
    f0 = float(norm.pdf(x0))
    n = float(n)
    alpha = float(alpha)
    if hs:
        return (
            n ** (-1.0 / 3.0)
            * float(norm.ppf(1.0 - alpha / 2.0)) ** (2.0 / 3.0)
            * ((1.5 * f0 * f0) / (2.0 * x0 * x0 + 1.0)) ** (1.0 / 3.0)
        )
    return n ** -0.2 * ((4.5 * f0 ** 4) / (2.0 * x0 * x0 + 1.0) ** 2) ** 0.2
