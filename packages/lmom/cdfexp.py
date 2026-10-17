from ._cdf_common import exp_cdf, scalarize

def cdfexp(x, para):
    return scalarize(x, exp_cdf(x, para[0], para[1]))
