from ._cdf_common import gam_cdf, scalarize

def cdfgam(x, para):
    return scalarize(x, gam_cdf(x, para[0], para[1]))
