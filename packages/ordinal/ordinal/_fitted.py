"""Category probabilities from linear predictors (ordinal get_fitted.c)."""

import math

import numpy as np
from scipy.special import expit
from scipy.stats import cauchy, norm

from ordinal.links import pgumbel, plgamma


def _p_aranda_ordaz(q, lam, lower_tail):
    if not math.isfinite(q):
        return q if math.isnan(q) else (1.0 if q > 0 else 0.0) if lower_tail else (0.0 if q > 0 else 1.0)
    if abs(lam) < 1e-15:
        return expit(q) if lower_tail else expit(-q)
    inner = 1.0 + lam * q
    if inner <= 0:
        return 0.0 if lower_tail else 1.0
    t = inner ** (1.0 / lam)
    return t / (1.0 + t) if lower_tail else 1.0 / (1.0 + t)


def get_fitted(eta1, eta2, link, lambda_=1.0):
    """Probabilities P(Y=j) from cumulative link thresholds."""
    e1 = np.asarray(eta1, dtype=float).reshape(-1)
    e2 = np.asarray(eta2, dtype=float).reshape(-1)
    if e2.size != e1.size:
        raise ValueError("'eta1' and 'eta2' should have the same length")
    link = str(link)
    lam = float(lambda_)
    out = np.empty_like(e1)
    for i in range(e1.size):
        a, b = e1[i], e2[i]
        if link == "probit":
            if b <= 0:
                out[i] = norm.cdf(a) - norm.cdf(b)
            else:
                out[i] = norm.sf(b) - norm.sf(a)
        elif link == "logit":
            if b <= 0:
                out[i] = expit(a) - expit(b)
            else:
                out[i] = expit(-b) - expit(-a)
        elif link == "loglog":
            # src/get_fitted.c: d_pgumbel(q, lower) for eta2 <= 0, upper tail otherwise
            if b <= 0:
                out[i] = pgumbel(a, max=True)[0] - pgumbel(b, max=True)[0]
            else:
                out[i] = pgumbel(b, max=True, lower_tail=False)[0] - pgumbel(
                    a, max=True, lower_tail=False
                )[0]
        elif link == "cloglog":
            # src/get_fitted.c: d_pgumbel2(q, lower) for eta2 <= 0, upper tail otherwise
            if b <= 0:
                out[i] = pgumbel(a, max=False)[0] - pgumbel(b, max=False)[0]
            else:
                out[i] = pgumbel(b, max=False, lower_tail=False)[0] - pgumbel(
                    a, max=False, lower_tail=False
                )[0]
        elif link == "cauchit":
            if b <= 0:
                out[i] = cauchy.cdf(a) - cauchy.cdf(b)
            else:
                out[i] = cauchy.sf(b) - cauchy.sf(a)
        elif link == "Aranda-Ordaz":
            if b <= 0:
                out[i] = _p_aranda_ordaz(a, lam, True) - _p_aranda_ordaz(b, lam, True)
            else:
                out[i] = _p_aranda_ordaz(b, lam, False) - _p_aranda_ordaz(a, lam, False)
        elif link == "log-gamma":
            if b <= 0:
                out[i] = plgamma(a, lam)[0] - plgamma(b, lam)[0]
            else:
                out[i] = plgamma(b, lam, lower_tail=False)[0] - plgamma(
                    a, lam, lower_tail=False
                )[0]
        else:
            raise ValueError("link not recognized")
    return out
