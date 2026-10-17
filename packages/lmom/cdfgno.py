from ._cdf_common import gno_cdf, scalarize

def cdfgno(x, para):
    return scalarize(x, gno_cdf(x, para[0], para[1], para[2]))
