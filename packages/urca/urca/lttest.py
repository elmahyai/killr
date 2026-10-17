"""Likelihood ratio test for no linear trend in a VAR (``lttest``)."""

import numpy as np

from urca.johansen import CaJo, _pchisq, ca_jo


def lttest(z, r):
    """Likelihood ratio test for no inclusion of a linear trend in a VAR."""
    if not isinstance(z, CaJo):
        raise ValueError("\nObject 'x' must be of class 'ca.jo'\n")
    r = int(r)
    if r >= z.P or r < 1:
        raise ValueError("\nProvide number of cointegration vectors in valid range.\n")
    idx = r
    df = z.P - r
    n = z.Z0.shape[0]
    test1 = ca_jo(z.x, ecdet="const", K=z.lag, season=z.season, dumvar=z.dumvar)
    lambda1 = np.asarray(test1.lambda_, dtype=float)
    test2 = ca_jo(z.x, ecdet="none", K=z.lag, season=z.season, dumvar=z.dumvar)
    lambda2 = np.asarray(test2.lambda_, dtype=float)
    lam1 = lambda1[idx:z.P]
    lam2 = lambda2[idx:z.P]
    teststat = -n * np.sum(np.log((1.0 - lam1) / (1.0 - lam2)))
    pval = 1.0 - _pchisq(float(teststat), df, lower_tail=True)
    result = np.array([[teststat, pval]])
    print("LR-test for no linear trend")
    print()
    print(f"H0: H*2(r<={r})")
    print(f"H1: H2(r<={r})")
    print()
    print("Test statistic is distributed as chi-square")
    print(f"with {df} degress of freedom")
    rounded = np.round(result, 2)
    row = f"LR test{' ' * 8}{rounded[0, 0]:>11.2f}{rounded[0, 1]:>8.2f}"
    print(f"{'':>8}test statistic p-value")
    print(row)
    return result
