import numpy as np
from .se import se
def mse(actual, predicted):
    return float(np.mean(se(actual,predicted)))
