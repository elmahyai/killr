from ._common import sample_lmom


def samlmu(x, nmom=4, sort_data=True, ratios=None, trim=0):
    """Unbiased sample L-moments (or L-moment ratios)."""
    return sample_lmom(x, nmom, sort_data, ratios, trim)
