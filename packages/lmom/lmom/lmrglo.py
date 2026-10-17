from ._common import lmr


def lmrglo(para, nmom: int = 5):
    return lmr("lmr_glo", para, nmom)
