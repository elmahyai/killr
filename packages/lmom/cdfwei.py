from ._cdf_common import scalarize, wei_cdf

def cdfwei(x, para):
    return scalarize(x, wei_cdf(x, para[0], para[1], para[2]))
