from ._common import lmr


def lmrgam(para, nmom: int = 5):
    return lmr("lmr_gam", para, nmom)
