from ._common import lmr


def lmrgev(para, nmom: int = 5):
    return lmr("lmr_gev", para, nmom)
