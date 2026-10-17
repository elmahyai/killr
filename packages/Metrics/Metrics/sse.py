import numpy as np
from .se import se
def sse(actual, predicted):
    return float(np.sum(se(actual,predicted)))
