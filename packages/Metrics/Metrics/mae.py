import numpy as np
from .ae import ae
def mae(actual, predicted):
    return float(np.mean(ae(actual,predicted)))
