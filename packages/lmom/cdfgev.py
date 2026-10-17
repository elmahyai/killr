from ._cdf_common import gev_cdf, scalarize

def cdfgev(x, para):
    return scalarize(x, gev_cdf(x, para[0], para[1], para[2]))
