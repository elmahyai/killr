import numpy as np
from .ae import ae
def mdae(actual, predicted):
    return float(np.median(ae(actual,predicted)))
