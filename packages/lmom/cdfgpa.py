from ._cdf_common import gpa_cdf, scalarize

def cdfgpa(x, para):
    return scalarize(x, gpa_cdf(x, para[0], para[1], para[2]))
