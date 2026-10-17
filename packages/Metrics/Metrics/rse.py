import numpy as np
from .sse import sse
def rse(actual, predicted):
    a=np.asarray(actual,dtype=float)
    return float(sse(a,predicted)/sse(a,np.mean(a)))
