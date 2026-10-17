from ._cdf_common import glo_cdf, scalarize

def cdfglo(x, para):
    return scalarize(x, glo_cdf(x, para[0], para[1], para[2]))
