from .pelq import _fit


def pelp(lmom, pfunc, start, type="n", **kwargs):
    """Estimate parameters by matching L-moments of a CDF."""
    return _fit(lmom, pfunc, start, type, True, **kwargs)
