import numpy as np
from .ll import ll
def logLoss(actual, predicted):
    return float(np.mean(ll(actual,predicted)))
