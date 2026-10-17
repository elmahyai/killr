from ._cdf_common import nor_cdf, scalarize

def cdfnor(x, para):
    return scalarize(x, nor_cdf(x, para[0], para[1]))
