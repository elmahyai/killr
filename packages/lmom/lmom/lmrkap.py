from ._common import lmr


def lmrkap(para, nmom: int = 5):
    return lmr("lmr_kap", para, nmom)
