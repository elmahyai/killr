import numpy as np
from .ape import ape
def mape(actual, predicted):
    return float(np.mean(ape(actual,predicted)))
