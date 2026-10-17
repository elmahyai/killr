"""Bounded glm links used for pseudovalues."""

import math

from survival.norm import qnorm


def _clamp(mu, edge, upper=True):
    values = [float(value) for value in mu]
    out = []
    for value in values:
        if upper:
            value = min(value, 1.0 - edge)
        if value < edge:
            value = edge
        out.append(value)
    return out


def blogit(edge=0.05):
    """Logit link that clamps the mean away from 0 and 1."""

    def linkfun(mu):
        return [math.log(x / (1.0 - x)) for x in _clamp(mu, edge)]

    return {"linkfun": linkfun, "name": "blogit"}


def bcloglog(edge=0.05):
    """Complementary log-log link that clamps the mean away from 0 and 1."""

    def linkfun(mu):
        return [math.log(-math.log(1.0 - x)) for x in _clamp(mu, edge)]

    return {"linkfun": linkfun, "name": "bcloglog"}


def bprobit(edge=0.05):
    """Probit link that clamps the mean away from 0 and 1. The name stays probit."""

    def linkfun(mu):
        return [qnorm(x) for x in _clamp(mu, edge)]

    return {"linkfun": linkfun, "name": "probit"}


def blog(edge=0.05):
    """Log link that clamps the mean at edge."""

    def linkfun(mu):
        return [math.log(max(edge, float(value))) for value in mu]

    return {"linkfun": linkfun, "name": "blog"}
