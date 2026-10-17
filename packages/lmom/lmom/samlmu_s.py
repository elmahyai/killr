from ._common import sample_lmom


def samlmu_s(x, nmom=4, sort_data=True, ratios=None, trim=0):
    """Pure-Python equivalent of lmom::samlmu.s."""
    return sample_lmom(x, nmom, sort_data, ratios, trim)
