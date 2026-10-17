import numpy as np
from .rse import rse
def rrse(actual, predicted):
    return float(np.sqrt(rse(actual,predicted)))
