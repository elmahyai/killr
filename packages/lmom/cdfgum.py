from ._cdf_common import gum_cdf, scalarize

def cdfgum(x, para):
    return scalarize(x, gum_cdf(x, para[0], para[1]))
