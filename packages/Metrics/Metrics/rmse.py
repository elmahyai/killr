import numpy as np
from .mse import mse
def rmse(actual, predicted):
    return float(np.sqrt(mse(actual,predicted)))
