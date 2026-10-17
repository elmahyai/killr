from ._common import lmr


def lmrgpa(para, nmom: int = 5):
    return lmr("lmr_gpa", para, nmom)
