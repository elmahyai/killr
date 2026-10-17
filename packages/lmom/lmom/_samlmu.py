from ._common import sample_lmom


def _samlmu(x, nmom=4):
    """Bare-bones sample L-moment-ratio routine."""
    return sample_lmom(x, nmom, True, True, 0)
