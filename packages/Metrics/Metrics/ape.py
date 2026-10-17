import numpy as np
from .ae import ae
def ape(actual, predicted):
    with np.errstate(divide="ignore", invalid="ignore"):
        return ae(actual,predicted)/np.abs(np.asarray(actual,dtype=float))
