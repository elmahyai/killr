from ._common import lmr


def lmrnor(para, nmom: int = 5):
    return lmr("lmr_nor", para, nmom)
