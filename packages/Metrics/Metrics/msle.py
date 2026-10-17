import numpy as np
from .sle import sle
def msle(actual, predicted):
    return float(np.mean(sle(actual,predicted)))
